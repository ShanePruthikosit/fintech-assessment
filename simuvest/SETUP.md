# SimuVest - Quick Setup Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Start the Backend

```bash
python3 main.py
```

You should see:
```
✓ Database initialized
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Open the Frontend

Open `frontend/index.html` in your web browser, or serve it with:

```bash
cd frontend
python3 -m http.server 3000
```

Then visit: `http://localhost:3000`

## ✅ Verify It's Working

1. You should see the SimuVest interface with:
   - Portfolio showing $100,000 cash
   - Market panel showing 8 stocks
   - Trading interface on the right

2. Test a trade:
   - Click on AAPL stock
   - Enter quantity: 10
   - Click BUY
   - Your portfolio should update immediately

## 📚 API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation

## 🧪 Run Tests

```bash
# Make sure backend is running first
python3 test-api.py
```

## 🐳 Docker Alternative

```bash
docker-compose up --build
```

Then visit: `http://localhost`

## 📋 Project Structure

```
simuvest/
├── backend/           # FastAPI server
├── frontend/          # React interface  
├── nginx/            # Web server config
├── data/             # SQLite database
└── docs/             # Documentation
```

## 🆘 Troubleshooting

### Backend won't start
- Make sure Python 3.11+ is installed
- Check if port 8000 is available
- Verify all dependencies installed

### Frontend shows errors
- Make sure backend is running
- Check browser console for errors
- Verify CORS is enabled in backend

### Database errors
- Delete `data/simuvest.db` and restart
- Check file permissions on data directory

## 📞 Need Help?

See the full documentation in:
- `README.md` - Complete documentation
- `PROJECT_OVERVIEW.md` - Technical details

---

**Ready to trade! Good luck! 📈**
