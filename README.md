# ThothAI - Unified Text-to-SQL Platform

<div align="center">
  <img src="frontend/public/dio-thoth-dx.png" alt="ThothAI Logo" width="200"/>
  
  **Advanced AI-powered Text-to-SQL generation platform**
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://hub.docker.com/r/marcopancotti/thoth)
  [![Python](https://img.shields.io/badge/Python-3.13-green.svg)](https://www.python.org/)
  [![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
</div>

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI

# 2. Copy environment template and configure
cp .env.template .env
# Edit .env with your API keys

# 3. Start all services
docker-compose up -d

# 4. Access the application
# Frontend: http://localhost:3001
# Backend Admin: http://localhost:8040/admin
# API: http://localhost:8040/api
```

### Using Pre-built Docker Image

```bash
# Pull and run the latest image
docker run -d \
  --name thoth \
  -p 80:80 \
  -v $(pwd)/exports:/app/exports \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -e OPENAI_API_KEY=your-key \
  -e LOGFIRE_TOKEN=your-token \
  marcopancotti/thoth:latest
```

## 📋 Prerequisites

- Docker & Docker Compose
- At least one LLM API key (OpenAI, Gemini, or Anthropic)
- 4GB RAM minimum
- 5GB disk space

## 🏗️ Architecture

```
ThothAI/
├── backend/          # Django backend (API & Admin)
├── frontend/         # Next.js frontend
├── docker/           # Dockerfiles
├── scripts/          # Utility scripts
├── exports/          # Data exports
├── logs/            # Application logs
└── data/            # Persistent data
```

### Services

- **Backend**: Django REST API with admin interface
- **Frontend**: Next.js React application
- **SQL Generator**: AI-powered SQL generation service
- **PostgreSQL**: Main database
- **Qdrant**: Vector database for embeddings
- **Nginx Proxy**: Reverse proxy and static file serving

## 🔧 Configuration

### Required Environment Variables

```env
# LLM API Keys (at least one required)
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-anthropic-key

# Embedding Service
EMBEDDING_API_KEY=your-embedding-key
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Optional: Monitoring
LOGFIRE_TOKEN=your-logfire-token
```

### Port Configuration

Default ports (configurable in .env):
- Web Interface: 80
- Backend API: 8040
- Frontend: 3001
- SQL Generator: 8005

## 🛠️ Development

### Local Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Run all tests
./scripts/test-local.sh

# Backend tests only
cd backend && python manage.py test

# Frontend tests only
cd frontend && npm test
```

## 🚢 Deployment

### Building for Production

```bash
# Build multi-architecture image
./scripts/build-unified.sh v1.0.0

# Build locally
docker-compose build
```

### Docker Hub Publishing

```bash
# Requires Docker Hub account
docker login
./scripts/build-unified.sh v1.0.0
```

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [API Documentation](docs/API.md)
- [Development Guide](docs/DEVELOPMENT.md)

## 🔒 Security

- All API keys should be kept secure and never committed to version control
- Use strong passwords for database and admin accounts
- Enable HTTPS in production environments
- Regularly update dependencies

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 👥 Authors

- **Marco Pancotti** - *Initial work* - [mptyl](https://github.com/mptyl)

## 🙏 Acknowledgments

- OpenAI for GPT models
- Google for Gemini models
- Anthropic for Claude models
- All contributors and testers

## 📞 Support

- GitHub Issues: [https://github.com/mptyl/ThothAI/issues](https://github.com/mptyl/ThothAI/issues)
- Email: support@thoth.ai

---

<div align="center">
  Made with ❤️ by the ThothAI Team
</div>