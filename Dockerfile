# Use Ubuntu 24.10 as the base image for the builder stage
FROM ubuntu:24.10 AS builder

# Update the package manager and install essential dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Install Playwright browser dependencies
RUN npx playwright install-deps

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json to leverage Docker caching
COPY package*.json ./

# Install all development dependencies
RUN npm install --include=dev --audit=false

# Install Playwright browsers
RUN npx playwright install

# Copy source code and build the project
COPY . ./
RUN npm run build --output-path=/app/dist

# Use a smaller base image to create the final production image
FROM ubuntu:24.10

# Install Node.js runtime and required dependencies for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libglib2.0-0t64\
    libnss3\
    libnspr4\
    libdbus-1-3\
    libatk1.0-0t64\
    libatk-bridge2.0-0t64\
    libcups2t64\
    libdrm2\
    libxcb1\
    libxkbcommon0\
    libatspi2.0-0t64\
    libx11-6\
    libxcomposite1\
    libxdamage1\
    libxext6\
    libxfixes3\
    libxrandr2\
    libgbm1\
    libpango-1.0-0\
    libcairo2\
    libasound2t64\
    libxcursor1\
    libgtk-3-0t64\
    libpangocairo-1.0-0\
    libcairo-gobject2\
    libgdk-pixbuf-2.0-0\
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy built files from the builder stage
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

# Install production dependencies
RUN npm install --omit=dev --omit=optional

# Install Playwright browsers
RUN npx playwright install

# Command to start the application
CMD ["node", "/app/dist/main.js"]
