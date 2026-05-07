# PowerPoint-Layout-and-Style-Consistent-Webpage-Generation-System

A Flask-based web application that generates HTML presentations with consistent PowerPoint-style layouts and professional design.

## Features

- **Smart Document Parsing**: Uses LLM to intelligently parse and structure text content
- **Multiple Page Types**: Support for cover, table of contents, section dividers, and content pages
- **Template System**: Multiple design templates (tech, business, etc.)
- **Real-time Streaming**: Stream-generated slides for instant preview
- **Project Management**: Save and manage multiple presentation projects
- **RESTful API**: Complete API for integration with other systems

## Tech Stack

- **Backend**: Flask, Flask-CORS
- **Frontend**: Vue.js
- **Database**: SQLite (with SQLAlchemy ORM)
- **LLM Integration**: OpenAI GPT models

## Project Structure

```
PowerPoint-Layout-and-Style-Consistent-Webpage-Generation-System/
├── frontend/              # Vue.js frontend
├── backend/               # Backend Flask application
├── engine/                # Document parsing engine
├── generator/             # Content generation
├── pipeline/              # PPT generation pipeline
├── templates/             # HTML templates
├── database/              # Database models and services
├── services/              # Business logic services
├── config.py             # Configuration
└── app.py                 # Main Flask application
```

## API Endpoints

### Document Parsing
- `POST /api/parse-text` - Parse text content using LLM
- `POST /api/save-parse-result` - Save parse result to database
- `GET /api/get-parse-result/<project_id>` - Get parse result

### PPT Generation
- `POST /api/generate-ppt` - Generate PPT from topic/text
- `POST /api/generate-ppt-from-outline` - Generate PPT from outline
- `POST /api/generate-ppt-stream` - Stream-generated PPT
- `POST /api/generate-ppt-parallel` - Parallel PPT generation

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create project
- `GET /api/projects/<id>` - Get project details
- `PUT /api/projects/<id>` - Update project
- `DELETE /api/projects/<id>` - Delete project

## Setup

1. Install dependencies:
```bash
pip install flask flask-cors sqlalchemy python-pptx
```

2. Set environment variables:
```bash
export OPENAI_API_KEY=your_api_key
```

3. Run the application:
```bash
python app.py
```

4. Access the web interface at `http://localhost:5000`

## License

MIT
