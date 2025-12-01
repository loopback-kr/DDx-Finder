FROM ghcr.io/open-webui/mcpo:git-25b219a

# Install essential packages
RUN uv add fastmcp==2.12.4 beautifulsoup4