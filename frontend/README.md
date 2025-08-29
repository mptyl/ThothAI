# ThothAI UI

Modern React/Next.js frontend for the ThothAI natural language to SQL conversion system.

## Overview

ThothAI UI is a modern web interface built with Next.js 14, TypeScript, and Tailwind CSS. It provides a chatbot-style interface for interacting with the ThothAI system that converts natural language questions into SQL queries.

## Features

- 🔐 **Authentication Integration** - Seamlessly integrates with Django backend authentication
- 💬 **Chat Interface** - Chatbot-style conversation interface for natural language queries
- 🤖 **AI Question Validation** - Real-time question validation using AI agents
- 🗣️ **Voice Input** - Speech-to-text support with Whisper integration
- 🌙 **Dark/Light Theme** - Toggle between dark and light themes
- 📱 **Responsive Design** - Full-screen interface that works on all devices
- 🚀 **Modern Stack** - Built with Next.js 14, TypeScript, and Tailwind CSS
- 🐳 **Docker Support** - Multi-service containerized deployment
- ⚡ **FastAPI Integration** - Dedicated SQL generation service

## Prerequisites

- Node.js 18+ and npm
- Python 3.12+ (for SQL Generator service)
- Docker and Docker Compose (for containerized deployment)
- Django backend (thoth_be) running on configured port
- OpenAI API key (for AI question validation)

## Quick Start

### Development Mode

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Configure environment**
   ```bash
   cp .env.local.template .env.local
   # Edit .env.local to set NEXT_PUBLIC_DJANGO_SERVER
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Access the application**
   - Open http://localhost:3000
   - You'll be redirected to the login page

### Docker Development

1. **Start with Docker Compose**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

2. **Access the application**
   - Open http://localhost:3000

### Production Deployment

1. **Build and start with Docker Compose**
   ```bash
   docker-compose up --build
   ```

## Environment Configuration

The application uses the following environment variables:

- `NEXT_PUBLIC_DJANGO_SERVER` - URL of the Django backend (default: http://localhost:8040)
- `NODE_ENV` - Environment mode (development/production)
- `NEXTAUTH_URL` - Application URL (default: http://localhost:3000)
- `NEXTAUTH_SECRET` - Secret key for session management

## Project Structure

```
thoth_ui/
├── app/                    # Next.js 14 app router pages
│   ├── login/             # Login page
│   ├── welcome/           # Welcome/dashboard page
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page (redirects)
├── components/            # React components
│   ├── ui/               # Reusable UI components
│   ├── login-form.tsx    # Login form component
│   ├── welcome-screen.tsx # Welcome screen component
│   └── ...
├── lib/                   # Utilities and services
│   ├── api.ts            # API client for Django backend
│   ├── auth-context.tsx  # Authentication context
│   └── types.ts          # TypeScript type definitions
└── ...
```

## Authentication Flow

1. User accesses the application
2. If not authenticated, redirected to `/login`
3. Login form submits credentials to Django `/api/login` endpoint
4. On success, token and user data stored locally
5. User redirected to `/welcome` screen
6. Token included in subsequent API requests

## API Integration

The application integrates with the Django backend through:

- **Login**: `POST /api/login` - Authenticate user
- **Token Test**: `GET /api/test_token` - Validate stored token
- **Future endpoints**: Will integrate with SQL generation and workspace management

## Styling

The application uses:

- **Tailwind CSS** for utility-first styling
- **CSS Custom Properties** for theme variables
- **Responsive design** with mobile-first approach
- **Dark/light theme** support with system preference detection

## Development Commands

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Docker Commands

```bash
# Development with hot reload
docker-compose -f docker-compose.dev.yml up --build

# Production deployment
docker-compose up --build

# Stop containers
docker-compose down

# View logs
docker-compose logs thoth-ui
```

## Contributing

1. Follow the existing code style and patterns
2. Add appropriate TypeScript types
3. Include copyright headers in all new files
4. Test authentication flow before submitting changes

## Credits & Acknowledgments

### CHESS Framework

This project is powered by CHESS (Contextual Harnessing for Efficient SQL Synthesis):

```bibtex
@article{talaei2024chess,
  title={CHESS: Contextual Harnessing for Efficient SQL Synthesis},
  author={Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin},
  journal={arXiv preprint arXiv:2405.16755},
  year={2024}
}
```

## License

This project is released under the Apache License 2.0. See LICENSE.md for details.

## Next Steps

The current implementation provides the foundation for:

- Chat interface integration
- SQL query generation UI
- Database workspace management
- Result visualization
- Query history and sharing