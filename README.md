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
├── app.py                 # Main Flask application and API wiring
├── pipeline.py            # Presentation generation pipeline
├── database.py            # SQLite models/session setup
├── config.py              # Configuration
├── engine/                # Outline/content reasoning primitives
├── evaluator/             # Layout/style/readability quality metrics
├── framework/             # Design tokens, layouts, and components
├── frontend/              # Vue.js frontend
├── generator/             # LLM prompts, clients, and HTML generation
├── parsers/               # Text/PDF/DOCX/PPTX/Markdown parsing
├── routes/                # Flask route modules
├── scripts/               # Runtime/maintenance scripts used by the app
├── services/              # Business logic services
├── templates/             # Template models, loader, renderer, and data
└── test/                  # Automated tests, fixtures, and manual test scripts
```

Manual/integration scripts that call the API, LLM, or write generated artifacts live in
`test/manual/` and are not collected by default pytest discovery.

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

Backend:

```bash
python app.py
```

Frontend:

```bash
npm run dev
```

4. Access the web interface at `http://localhost:5173`

## License

MIT
