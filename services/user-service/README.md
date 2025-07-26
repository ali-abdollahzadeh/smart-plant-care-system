# User Service Dashboard

This service provides a centralized web dashboard for managing the Smart Plant Care System, along with a Telegram bot for mobile interactions.

## Features

### Web Dashboard
- **Modern, responsive UI** with beautiful styling
- **User Management**: Register and manage users
- **Plant Management**: Register and assign plants to users
- **Real-time Status**: Monitor plant health and sensor data
- **Actuator Control**: Control watering and LED systems
- **Statistics**: View system statistics and alerts

### Telegram Bot
- **Mobile Interface**: Access system features via Telegram
- **Plant Monitoring**: Get real-time plant status
- **Notifications**: Receive alerts and updates
- **Quick Actions**: Control actuators remotely

## Dashboard Pages

### 1. Main Dashboard (`/`)
- Overview of system statistics
- Quick access to all features
- Real-time status indicators

### 2. Register User (`/register_user`)
- Add new users to the system
- Support for Telegram integration
- User profile management

### 3. Register Plant (`/register_plant`)
- Add new plants to the system
- Configure plant thresholds
- Assign plants to users

### 4. Advanced Plant Registration (`/register_plant_advanced`)
- Use plant database for pre-configured plants
- Automatic threshold and care information
- Interactive plant selection
- Detailed plant information display

### 5. Assign Plant (`/assign_plant`)
- Link plants to users
- View current assignments
- Manage plant ownership

### 6. Plant Status (`/plant_status`)
- Real-time sensor data
- Plant health monitoring
- Actuator controls
- Status alerts and warnings

## API Endpoints

### Dashboard Routes
- `GET /` - Main dashboard
- `GET/POST /register_user` - User registration
- `GET/POST /register_plant` - Basic plant registration
- `GET/POST /register_plant_advanced` - Advanced plant registration with database
- `GET/POST /assign_plant` - Plant assignment
- `GET /plant_status` - Plant status overview
- `POST /actuator` - Actuator control
- `GET /health` - Health check

### Telegram Bot Routes
- `POST /notify` - Send notifications via Telegram

## Configuration

The service uses the following environment variables:

```yaml
# config.yaml
mqtt:
  broker_url: "localhost"
  port: 1883
  subscribe_topic: "plant/alerts"

# Environment variables
CONFIG_PATH: "config.yaml"
CATALOGUE_API_URL: "http://catalogue-service:5000"
SENSOR_API_URL: "http://sensor-service:5500"
```

## File Structure

```
services/user-service/
├── main.py              # Main application entry point
├── dashboard.py         # Dashboard Flask application
├── telegram_bot.py      # Telegram bot functionality
├── db.py               # Database operations
├── notifier.py         # Notification system
├── templates/          # HTML templates
│   ├── dashboard.html
│   ├── register_user.html
│   ├── register_plant.html
│   ├── assign_plant.html
│   └── plant_status.html
├── static/            # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── dashboard.js
├── config.yaml        # Configuration file
├── users.db          # SQLite database
└── requirements.txt  # Python dependencies
```

## Running the Service

### Development
```bash
cd services/user-service
python main.py
```

### Docker
```bash
docker-compose up user-service
```

The dashboard will be available at `http://localhost:5500`

## Integration

### With Other Services
- **Catalogue Service**: User and plant data management
- **Sensor Service**: Real-time sensor data and actuator control
- **Analytics Service**: Plant health analysis and recommendations
- **Cloud Adapter**: Data synchronization and external integrations

### Telegram Bot Integration
The Telegram bot provides mobile access to:
- Plant status monitoring
- Actuator controls
- Notifications and alerts
- Quick commands for common actions

## Features

### Modern UI/UX
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Auto-refresh plant status
- **Interactive Elements**: Hover effects and smooth animations
- **Status Indicators**: Color-coded plant health status
- **Form Validation**: Client-side and server-side validation

### Data Management
- **Local Database**: SQLite for user data
- **Service Integration**: REST API calls to other services
- **Error Handling**: Graceful error handling and user feedback
- **Data Synchronization**: Sync between local and catalogue services

### Security
- **Input Validation**: Sanitize all user inputs
- **Error Logging**: Comprehensive error logging
- **Health Checks**: Service health monitoring

## Development

### Adding New Features
1. Create new template in `templates/`
2. Add route in `dashboard.py`
3. Update navigation in templates
4. Add any required static assets

### Styling
- CSS is in `static/css/style.css`
- Uses modern CSS Grid and Flexbox
- Responsive design with mobile-first approach
- Font Awesome icons for visual elements

### JavaScript
- Dashboard functionality in `static/js/dashboard.js`
- Auto-refresh capabilities
- Form validation
- Notification system
- Smooth animations

## Troubleshooting

### Common Issues
1. **Database errors**: Check `users.db` permissions
2. **Service connectivity**: Verify other services are running
3. **Template errors**: Check Jinja2 syntax in templates
4. **Static files**: Ensure static folder structure is correct

### Logs
Check application logs for detailed error information:
```bash
docker-compose logs user-service
```

## Contributing

When adding new features:
1. Follow the existing code structure
2. Add proper error handling
3. Update documentation
4. Test on different screen sizes
5. Ensure mobile compatibility 