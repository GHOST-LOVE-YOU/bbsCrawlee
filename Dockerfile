# First, specify the base Docker image.
# You can see the Docker images from Apify at https://hub.docker.com/r/apify/.
# You can also use any other image from Docker Hub.
# Currently camoufox has issues installing on Python 3.13
FROM apify/actor-python-playwright:3.12
RUN apt update && apt install -yq git && rm -rf /var/lib/apt/lists/*

RUN pip install -U pip setuptools \
    && pip install 'uv<1'

ENV UV_PROJECT_ENVIRONMENT="/usr/local"

COPY pyproject.toml uv.lock ./

RUN echo "Python version:" \
    && python --version \
    && echo "Installing dependencies:" \
    # Check if playwright is already installed
    && PLAYWRIGHT_INSTALLED=$(pip freeze | grep -q playwright && echo "true" || echo "false") \
    && if [ "$PLAYWRIGHT_INSTALLED" = "true" ]; then \
        echo "Playwright already installed, excluding from uv sync" \
        && uv sync --frozen --no-install-project --no-editable -q --no-dev --inexact --no-install-package playwright; \
    else \
        echo "Playwright not found, installing all dependencies" \
        && uv sync --frozen --no-install-project --no-editable -q --no-dev --inexact; \
    fi \
    && echo "All installed Python packages:" \
    && pip freeze
# Next, copy the remaining files and directories with the source code.
# Since we do this after installing the dependencies, quick build will be really fast
# for most source file changes.
COPY . ./

# Use compileall to ensure the runnability of the Actor Python code.
RUN python -m compileall -q .

# Fetch camoufox files that are always needed when using camoufox.
RUN python -m camoufox fetch
# Specify how to launch the source code of your Actor.
CMD ["python", "-m", "iwhisper"]
