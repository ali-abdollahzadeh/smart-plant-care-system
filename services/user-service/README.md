# User Service

The User Service manages user interactions and notifications for the Smart Plant Care System. It provides a Telegram bot for user commands, handles notifications, and offers web interfaces for plant and user management.

## 🎯 Purpose

- **Telegram Bot**: Provide user interface for plant monitoring and control
- **User Notifications**: Send alerts and updates to users via Telegram
- **Web Interface**: Offer web forms for plant and user management
- **Alert Management**: Process MQTT alerts and forward to appropriate users
- **User Database**: Manage user accounts and plant assignments

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram      │    │   Web           │    │   MQTT          │
│   Bot           │    │   Interface     │    │   Alert         │
│   (User Commands)│   │   (Forms)       │    │   Handler       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   User          │
                    │   Service       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   SQLite DB     │
                    │   (User Data)   │
                    └─────────────────┘
```

## 🚀 Quick Start

### Running with Docker
```bash
docker-compose up user-service
```

### Running Locally
```bash
cd services/user-service
pip install -r requirements.txt
python main.py
```

### Access Points
- **Telegram Bot**: Search for your bot username
- **Web Interface**: http://localhost:5500
- **REST API**: http://localhost:5500

## 📋 API Endpoints

### User Management

#### Register User
```http
POST /users
Content-Type: application/json

{
  "username": "john_doe",
  "telegram_id": "123456789",
  "display_name": "John Doe"
}
```

#### Get User
```http
GET /users/{user_id}
```

#### Update User
```http
PATCH /users/{user_id}
Content-Type: application/json

{
  "telegram_id": "123456789",
  "active": true
}
```

### Plant Management

#### Assign Plant to User
```http
POST /assign_plant
Content-Type: application/json

{
  "user_id": "user-uuid",
  "plant_id": "plant-uuid"
}
```

#### Get User's Plants
```http
GET /users/{user_id}/plants
```

### Notifications

#### Send Notification
```http
POST /notify
Content-Type: application/json

{
  "user_id": "user-uuid",
  "message": "Your plant needs watering!",
  "type": "alert"
}
```

## 🤖 Telegram Bot Commands

### Basic Commands
- `/start` - Welcome message and bot introduction
- `/help` - Show available commands
- `/status` - Get current plant status
- `/plants` - List your assigned plants

### Plant Control
- `/water {plant_id}` - Manually trigger watering
- `/led {plant_id} {on/off}` - Control LED indicator
- `/fan {plant_id} {on/off}` - Control ventilation fan

### Monitoring
- `/temperature {plant_id}` - Get temperature reading
- `/humidity {plant_id}` - Get humidity reading
- `/moisture {plant_id}` - Get soil moisture reading
- `/all {plant_id}` - Get all sensor readings

### Settings
- `/thresholds {plant_id}` - View plant thresholds
- `/set_threshold {plant_id} {metric} {min} {max}` - Update thresholds
- `/alerts {on/off}` - Enable/disable alerts

## 🌐 Web Interface

### Plant Registration Form
- **URL**: http://localhost:5500/register_plant
- **Features**: 
  - Dropdown selection from plant database
  - User assignment options
  - Threshold configuration

### User Registration Form
- **URL**: http://localhost:5500/register_user
- **Features**:
  - Username and display name
  - Telegram ID linking
  - Account activation

### Plant Assignment Form
- **URL**: http://localhost:5500/assign_plant
- **Features**:
  - User selection dropdown
  - Plant selection dropdown
  - Assignment confirmation

## 🔧 Configuration

### Environment Variables
- `CONFIG_PATH`: Path to global configuration file
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `CATALOGUE_URL`: URL for catalogue service

### Telegram Configuration
```yaml
telegram:
  bot_token: "7105387626:AAHyiexS3gA5XPhkox16NfVRq9hAx8FxcA8"
```

### MQTT Configuration
```yaml
mqtt:
  broker_url: "mqtt-broker"
  port: 1883
  subscribe_topic: "plant/commands"
```

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    telegram_id TEXT,
    display_name TEXT,
    active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User Plants Table
```sql
CREATE TABLE user_plants (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    plant_id TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (plant_id) REFERENCES plants (id)
);
```

### Notifications Table
```sql
CREATE TABLE notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    message TEXT,
    type TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## 📈 Usage Examples

### Register User via API
```python
import requests

user_data = {
    "username": "alice_smith",
    "telegram_id": "987654321",
    "display_name": "Alice Smith"
}

response = requests.post("http://localhost:5500/users", json=user_data)
user_id = response.json()["id"]
print(f"User registered with ID: {user_id}")
```

### Send Notification
```python
import requests

notification = {
    "user_id": "user-uuid",
    "message": "🌱 Your Monstera needs watering! Current soil moisture: 250",
    "type": "alert"
}

response = requests.post("http://localhost:5500/notify", json=notification)
print(f"Notification sent: {response.status_code}")
```

### Get User's Plants
```python
import requests

response = requests.get("http://localhost:5500/users/user-uuid/plants")
plants = response.json()

for plant in plants:
    print(f"Plant: {plant['name']} ({plant['species']})")
    print(f"Location: {plant['location']}")
```

### Telegram Bot Integration
```python
# Example of custom bot command
@bot.message_handler(commands=['custom_command'])
def handle_custom_command(message):
    user_id = message.from_user.id
    
    # Get user's plants
    response = requests.get(f"http://localhost:5500/users/{user_id}/plants")
    plants = response.json()
    
    if plants:
        reply = "Your plants:\n"
        for plant in plants:
            reply += f"• {plant['name']} ({plant['species']})\n"
    else:
        reply = "You don't have any plants assigned yet."
    
    bot.reply_to(message, reply)
```

## 🔍 Monitoring

### Available Endpoints
- **Send Notification**: POST http://localhost:5500/notify
- **Register Plant**: http://localhost:5500/register_plant (GET/POST)
- **Assign Plant**: http://localhost:5500/assign_plant (GET/POST)

### MQTT Topics
- **Subscribe**: `plant/commands` (general commands)
- **Subscribe**: `plant/alerts` (alert messages)

### Logs
```bash
# View service logs
docker-compose logs user-service

# Follow logs in real-time
docker-compose logs -f user-service
```

## 🛠️ Development

### Adding New Bot Commands
1. Update `telegram_bot.py` with new command handlers
2. Add corresponding API endpoints if needed
3. Update help message with new commands
4. Test with Telegram bot

### Custom Notification Types
```python
# Example: Add custom notification type
def send_custom_notification(user_id, notification_type, data):
    if notification_type == "watering_reminder":
        message = f"💧 Time to water your {data['plant_name']}!"
    elif notification_type == "temperature_alert":
        message = f"🌡️ Temperature alert: {data['temperature']}°C"
    
    notification = {
        "user_id": user_id,
        "message": message,
        "type": notification_type
    }
    
    requests.post("http://localhost:5500/notify", json=notification)
```

### Extending Web Interface
```python
# Example: Add new web form
@app.route('/plant_settings', methods=['GET', 'POST'])
def plant_settings():
    if request.method == 'POST':
        plant_id = request.form['plant_id']
        thresholds = {
            'temperature': {
                'min': request.form['temp_min'],
                'max': request.form['temp_max']
            }
        }
        # Update plant thresholds
        return redirect('/plant_settings')
    
    # Show form
    return render_template('plant_settings.html')
```

## 📱 Telegram Bot Features

### Interactive Menus
- **Inline keyboards** for plant selection
- **Reply keyboards** for common actions
- **Callback queries** for dynamic responses

### Message Types
- **Text messages** for commands and responses
- **Photo messages** for plant images
- **Document messages** for reports

### Alert Types
- **Critical**: Immediate action required
- **Warning**: Monitor closely
- **Info**: Normal updates

## 🐛 Troubleshooting

### Common Issues

1. **Telegram Bot Not Responding**
   - Verify bot token is correct
   - Check bot is not blocked by user
   - Verify webhook or polling is working
   - Check service logs

2. **Notifications Not Sending**
   - Verify user has Telegram ID
   - Check user is active
   - Verify MQTT connection
   - Review notification format

3. **Web Forms Not Loading**
   - Check port 5500 is accessible
   - Verify Flask app is running
   - Check database connection
   - Review form templates

4. **User Registration Issues**
   - Verify username uniqueness
   - Check database permissions
   - Review registration logic
   - Test with sample data

### Debug Commands
```bash
# Test Telegram bot
curl -X POST "https://api.telegram.org/botYOUR_TOKEN/getMe"

# Check web interface
curl http://localhost:5500/health

# Test notification
curl -X POST http://localhost:5500/notify \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"Test notification"}'

# Check service status
docker-compose logs user-service
```

### Performance Monitoring
```bash
# Monitor bot response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5500/health

# Check service resource usage
docker stats user-service

# Monitor Telegram API calls
grep "telegram" docker-compose logs user-service
```

## 📚 Related Services

- **Catalogue Service**: Manages user and plant data
- **Sensor Service**: Receives user commands via Telegram
- **Analytics Service**: Sends alerts and notifications
- **Cloud Adapter**: May provide data for user queries 