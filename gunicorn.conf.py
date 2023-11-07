# Standard config section
import multiprocessing

max_requests = 1000
max_requests_jitter = 50

log_file = "-"

workers = multiprocessing.cpu_count() * 2 + 1
