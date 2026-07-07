require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });
const supertest = require('supertest');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

const api = supertest(BASE_URL);

module.exports = { api, BASE_URL };
