const { parsed } = require('dotenv-safe').config({allowEmptyValues: true, debug: true});
import CopyWebpackPlugin from 'copy-webpack-plugin';

export default function (config, env, helpers) {
    // dotenv injection: copy only the env variables defined in the .env file
    // use the values from current `process.env` not `parsed` because dotenv correctly handles env variables there
    const { plugin } = helpers.getPluginsByName(config, 'DefinePlugin')[0];
    for (let key of Object.keys(parsed)) {
        plugin.definitions[`process.env.${key}`] = JSON.stringify(process.env[key]);
    }

    console.log(`Using the server at ${process.env.SERVER_URL}:${process.env.SERVER_PORT}`)

    // load assets from assets folders
    config.plugins.push( new CopyWebpackPlugin([{ context: `${__dirname}/src/assets`, from: `*.*` }]) );
}