# 🔄 CampusTrade

A modern web application for campus bartering and trade offers. Built with Flask and designed for university students to exchange items seamlessly.

## 🌟 Features

### 🔐 Authentication & Security
- **User Registration & Login** - Secure account creation and authentication
- **Session Management** - Persistent login sessions
- **Password Hashing** - Secure password storage using Werkzeug
- **Route Protection** - Automatic redirect to login for protected pages

### 💼 Barter Management
- **Available Barters** - View items available for trade
- **Unfulfilled Requests** - Browse items students are looking for
- **Toggle Views** - Easy switching between barters and requests
- **Ownership Tracking** - Each entry tracks who created it

### 🤝 Trade System
- **Click to Trade** - Click on any available barter to initiate an offer
- **Trade Offer Form** - Modal popup for submitting trade proposals
- **Offer Tracking** - View all trade offers you've made
- **Contact Information** - Exchange details for follow-up

### 🎨 User Experience
- **Responsive Design** - Works on desktop and mobile devices
- **Bootstrap UI** - Modern, clean interface
- **Real-time Updates** - Instant form submissions and view toggling
- **Empty State Handling** - Helpful prompts when no data exists

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd campus-trade
2. **Create virtual environment (Recommended)**
   ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
4. **Set environment variable**
   ```bash
   export SECRET_KEY="your-secret-key-here"
5. **Run the application**
   ```bash
   python app.py

###🙏 Acknowledgments

- Flask community for excellent documentation
- Bootstrap for the UI framework
- Render for seamless deployment hosting
