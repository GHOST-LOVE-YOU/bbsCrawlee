FROM apify/actor-node-playwright-chrome:20 AS builder

USER root

# Copy just package.json and package-lock,json to speed up the build 
COPY package*.json ./

# Install all dependencies
RUN npm install --include=dev --audit=false

# Cope the source files
COPY . .

# build the project
RUN npm run build --output-path=/dist

# create the finial image
FROM apify/actor-node-playwright-chrome:20

# Switch to root user in the final image as well
USER root

#Cope only built js file from builder image
COPY --from=builder /dist ./dist

COPY package*.json ./

# Install npm packages, skip skip optional and development dependencies
# to keep the image small.
RUN npm --quiet set progress=false \
    && npm install --omit=dev --omit=optional \
    && echo "Installed NPM packages:" \
    && (npm list --omit=dev --all || true) \
    && echo "Node.js version:" \
    && node --version \
    && echo "NPM version:" \
    && npm --version

COPY . ./

RUN chmod +x ./start_xvfb_and_run_cmd.sh

CMD ["sh", "-c", "./start_xvfb_and_run_cmd.sh && npm run start:prod --silent"]
