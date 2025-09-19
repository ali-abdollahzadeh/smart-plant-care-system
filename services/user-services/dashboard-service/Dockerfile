FROM nodered/node-red:latest
# Copy Node-RED flow and settings files into /data
COPY --chown=node-red:node-red data/flows.json /data/flows.json
COPY --chown=node-red:node-red data/settings.js /data/settings.js
