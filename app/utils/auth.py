from typing import Dict, Optional, no_type_check
from urllib.parse import unquote

from fastapi import HTTPException, Request, status
from fastapi.openapi.models import OAuthFlowPassword, OAuthFlows as OAuthFlowsModel
from fastapi.param_functions import Form
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param


class OAuth2PasswordBearerWithCookie(OAuth2):
    @no_type_check
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            password=OAuthFlowPassword(tokenUrl=tokenUrl, scopes=scopes)
        )
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str | None = request.cookies.get(
            "access_token"
        )  # changed to accept access token from httpOnly Cookie

        if authorization:
            authorization = unquote(authorization)

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


class OAuth2PasswordRequestFormWithEmail:
    def __init__(
        self,
        grant_type: str = Form(default=None, regex="password"),
        username: str = Form(default=...),
        password: str = Form(default=...),
        email: str = Form(default=""),
        scope: str = Form(default=""),
        client_id: Optional[str] = Form(default=None),
        client_secret: Optional[str] = Form(default=None),
    ):
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.email = email
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret
