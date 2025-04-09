### Hexlet tests and linter status:

[![Actions Status](https://github.com/Pikachy337/python-project-83/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/Pikachy337/python-project-83/actions)
[![Python CI](https://github.com/Pikachy337/python-project-83/actions/workflows/ci.yml/badge.svg)](https://github.com/Pikachy337/python-project-83/actions/workflows/ci.yml)
<a href="https://qlty.sh/gh/Pikachy337/projects/python-project-83"><img src="https://qlty.sh/badges/393a03c6-5f02-417b-9a06-f5cd54d4ce55/maintainability.svg" alt="Maintainability" /></a>
<img src="https://cdn2.hexlet.io/store/derivatives/original/7bd880c9c167c174e27856dda2179f00.gif" alt="Гифка возможностей сайта">

## Live Demo

My deploy project: [https://python-project-83-82ns.onrender.com](https://python-project-83-82ns.onrender.com)

## Description

Page Analyzer is a web application that checks websites for availability and analyzes their SEO characteristics.

## Features

- URL validation
- Website availability checking
- SEO analysis (h1, title, description)
- History of checks for each URL

## Installation and Setup

1. Clone the Repository:

Begin by cloning the repository to your local machine using the following command:
```python
git clone git@github.com:Pikachy337/python-project-83
cd python-project-83
```

2. To use the application, you need to create a .env file in the root directory and add the SECRET_KEY and DATABASE_URL variables inside. For example:

```python
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url
```
Remember to replace these with your actual values and never commit your .env file to your repository!

3. Next, build and start the application using the following commands:
```python
make build
make start
```