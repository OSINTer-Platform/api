"""Please, do not under any circumstances touch this code. I don't know what transpired here
(or well, I do since I wrote it), but it is bad. Really bad"""

import io
import re
from string import Template
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token
import pymupdf

from modules.objects import FullArticle
from modules.files import generate_substitution_mapping

pymupdf.TOOLS.unset_quad_corrections(True)


class MarkdownPdf:
    """Converter class."""

    meta = {
        "creationDate": pymupdf.get_pdf_now(),
        "modDate": pymupdf.get_pdf_now(),
        "creator": "OSINTer",
        "producer": "PyMuPDF library: https://pypi.org/project/PyMuPDF",
        "author": "OSINTer",
    }

    def __init__(
        self,
        title: str,
        toc_level: int = 6,
        mode: str = "js-default",
        paper_size: str = "A4",
        borders: tuple[int, int, int, int] = (36, 36, -36, -36),
        template: Template | None = None,
    ):
        """Create md -> pdf converter with given TOC level and mode of md parsing."""
        self.toc_level = toc_level
        self.toc: list[Any] = []

        self.paper_size = paper_size
        self.borders = borders

        if template:
            self.template = template
        else:
            self.template = Template(
                """**$description**

+ Link: [$url]($url)
+ Source: $source
+ Author: $author
+ Date published: $publish_date
+ Date scraped: $scrape_date

$formatted_content

**Tags**:

$technical_tags

**Autogenerated tags**:

$auto_tags
"""
            )

        # zero, commonmark, js-default, gfm-like
        # https://markdown-it-py.readthedocs.io/en/latest/using.html#quick-start
        self.md = MarkdownIt(mode).enable("table")  # Enable support for tables

        self.out_file = io.BytesIO()
        self.writer = pymupdf.DocumentWriter(self.out_file)
        self.page = 0
        self.title = title

    @staticmethod
    def recorder(elpos: Any) -> None:
        """Call function invoked during story.place() for making a TOC."""
        if not elpos.open_close & 1:  # only consider "open" items
            return
        if not elpos.toc:
            return

        if 0 < elpos.heading <= elpos.pdfile.toc_level:  # this is a header (h1 - h6)
            elpos.pdfile.toc.append(
                (
                    elpos.heading,
                    elpos.text,
                    elpos.pdfile.page,
                    elpos.rect[1],  # top of written rectangle (use for TOC)
                )
            )

    @staticmethod
    def normalize_headings(
        tokens: list[Token], max_val: int = 2, min_val: int = 6
    ) -> list[Token]:
        biggest = 0

        for token in tokens[1:]:
            if token.type == "heading_open":
                level = int(token.tag[1:])
                biggest = min(level, biggest) if biggest else level

        if not biggest:
            return tokens

        # Used to prevent heading levels to drop multiple levels (e.g. h2 -> h4 would be invalid)
        last_normalized_level = 1
        last_corrected_level = 0

        for token in tokens:
            if token.type.startswith("heading"):
                level = int(token.tag[1:])

                if level == last_corrected_level:
                    token.tag = f"h{min(last_normalized_level + 1, min_val)}"
                else:
                    last_corrected_level = 0

                normalized_level = min(level - (biggest - max_val), min_val)

                if normalized_level - last_normalized_level > 1:
                    last_corrected_level = level
                    normalized_level = min(last_normalized_level + 1, min_val)
                else:
                    last_normalized_level = normalized_level

                token.tag = f"h{normalized_level}"

        return tokens

    def add_article(
        self, article: FullArticle, user_css: str | None = None, toc: bool = True
    ) -> None:
        # Need to remove empty headings, see https://github.com/pymupdf/PyMuPDF/issues/3559
        markdown_str = self.template.substitute(
            **generate_substitution_mapping(article)
        )
        markdown_str = re.sub(r"#{1,6}\s*$", "", markdown_str, flags=re.MULTILINE)

        normalized_tokens = self.normalize_headings(self.md.parse(markdown_str))
        title_tokens = self.md.parse(f"# {article.title}")

        html = self.md.renderer.render(
            title_tokens + normalized_tokens, self.md.options, {}
        )

        rect = pymupdf.paper_rect(self.paper_size)
        where = rect + self.borders
        story = pymupdf.Story(html=html, archive=".", user_css=user_css)

        more = 1
        while more:  # loop outputting the story
            self.page += 1
            device = self.writer.begin_page(rect)
            more, _ = story.place(where)  # layout into allowed rectangle
            story.element_positions(self.recorder, {"toc": toc, "pdfile": self})
            story.draw(device)
            self.writer.end_page()

    def save(self) -> io.BytesIO:
        """Save pdf to file."""
        self.writer.close()
        print(self.out_file.getbuffer().nbytes)
        doc: pymupdf.Document = pymupdf.Document("pdf", self.out_file)
        doc.set_metadata({**self.meta, "title": self.title})  # pyright: ignore

        if self.toc_level > 0:
            doc.set_toc(self.toc)  # pyright: ignore

        doc.save(self.out_file)
        return self.out_file
