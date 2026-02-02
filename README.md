# Community Feed - Playto Engineering Challenge

A full-stack community discussion platform with threaded comments, gamified karma system, and a dynamic 24-hour leaderboard.

![Community Feed Screenshot](screenshot.png)

## Features

- **Feed**: Text posts with author attribution and like counts
- **Threaded Comments**: Reddit-style nested comment threads
- **Gamification System**:
  - Post like = +5 karma to author
  - Comment like = +1 karma to author
- **24-Hour Rolling Leaderboard**: Shows top 5 users by karma earned in the last 24 hours
- **Concurrency Protection**: Database-level constraints prevent double-liking

## Tech Stack

- **Backend**: Django 5 + Django REST Framework
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Database**: SQLite (can easily switch to PostgreSQL)

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed demo data
python manage.py seed_data

# Start server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Visit `http://localhost:5173` to use the app.

### Demo Accounts

- **Users**: alice, bob, charlie, diana, ethan, fiona, george, hannah
- **Password**: password123

## Running Tests

```bash
cd backend
source venv/bin/activate
python manage.py test feed
```

## Docker Setup

```bash
docker-compose up --build
```

The app will be available at `http://localhost:3000`.

## Project Structure

```
.
├── backend/
│   ├── config/           # Django settings
│   ├── feed/             # Main app
│   │   ├── models.py     # Post, Comment, Like models
│   │   ├── views.py      # API viewsets
│   │   ├── serializers.py
│   │   └── tests.py      # Test cases
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── context/      # Auth context
│   │   └── services/     # API service
│   └── package.json
├── EXPLAINER.md          # Technical documentation
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts/` | List all posts |
| POST | `/api/posts/` | Create a post |
| GET | `/api/posts/{id}/` | Get post with comments |
| POST | `/api/posts/{id}/like/` | Like a post |
| POST | `/api/posts/{id}/unlike/` | Unlike a post |
| POST | `/api/comments/` | Create a comment |
| POST | `/api/comments/{id}/like/` | Like a comment |
| GET | `/api/leaderboard/` | Get 24h leaderboard |

## Technical Highlights

1. **N+1 Query Prevention**: Comments are fetched in a single query using materialized paths
2. **Concurrency Handling**: Database constraints + atomic transactions prevent race conditions
3. **Dynamic Karma Calculation**: Leaderboard computed from Like records, not stored values

See [EXPLAINER.md](EXPLAINER.md) for detailed technical documentation.

## License

MIT
