FROM node

WORKDIR /usr/src/app
COPY package*.json ./
RUN npm i

COPY . .

EXPOSE 8080

CMD ["/bin/bash", "run.sh"]
