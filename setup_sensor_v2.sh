#!/bin/bash

# Raspberry Pi Sensor System 2.0 Automated Setup Script
# This script sets up the complete sensor system on a fresh Raspberry Pi

set -e  # Exit on any error

echo "=================================================="
echo "  Raspberry Pi Sensor System 2.0 Setup Script"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root (don't use sudo)"
    exit 1
fi

# Get configuration from user
get_user_config() {
    echo ""
    print_step "Configuration Setup"
    echo "Please provide the following information:"
    
    read -p "Enter your header name (e.g., NATIONAL_1): " HEADER_NAME
    if [ -z "$HEADER_NAME" ]; then
        print_error "Header name is required!"
        exit 1
    fi
    
    read -p "Enter database server IP address [192.168.1.54]: " DB_HOST
    DB_HOST=${DB_HOST:-192.168.1.54}
    
    read -p "Enter database username [webapp]: " DB_USER
    DB_USER=${DB_USER:-webapp}
    
    read -p "Enter database password [STUDS2650]: " DB_PASS
    DB_PASS=${DB_PASS:-STUDS2650}
    
    read -p "Enter sensor GPIO pin [17]: " SENSOR_PIN
    SENSOR_PIN=${SENSOR_PIN:-17}
    
    echo ""
    print_status "Configuration summary:"
    echo "  Header Name: $HEADER_NAME"
    echo "  Database Host: $DB_HOST"
    echo "  Database User: $DB_USER"
    echo "  Sensor Pin: GPIO $SENSOR_PIN"
    echo ""
    
    read -p "Proceed with installation? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Installation cancelled."
        exit 0
    fi
}

# Update system packages
update_system() {
    print_step "Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    print_status "System updated successfully"
}

# Install system dependencies
install_system_deps() {
    print_step "Installing system dependencies..."
    
    # Python and development tools
    sudo apt install -y python3 python3-pip python3-venv python3-dev
    
    # Display and graphics libraries
    sudo apt install -y python3-pil python3-numpy
    sudo apt install -y libfreetype6-dev libjpeg-dev libopenjp2-7 libtiff5
    
    # GPIO library
    sudo apt install -y python3-rpi.gpio
    
    # Other utilities
    sudo apt install -y git curl wget nano
    
    print_status "System dependencies installed"
}

# Enable required Pi interfaces
enable_interfaces() {
    print_step "Enabling Raspberry Pi interfaces..."
    
    # Enable SPI for OLED display
    sudo raspi-config nonint do_spi 0
    
    # Enable I2C as backup
    sudo raspi-config nonint do_i2c 0
    
    # Ensure GPIO is accessible
    sudo usermod -a -G gpio $USER
    sudo usermod -a -G spi $USER
    
    print_status "Interfaces enabled (SPI, I2C, GPIO)"
}

# Create project directory and virtual environment
setup_project() {
    print_step "Setting up project directory..."
    
    PROJECT_DIR="/home/$USER/sensor_system"
    
    # Create directory
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # Create Python virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_status "Project directory created at $PROJECT_DIR"
}

# Install Python packages
install_python_deps() {
    print_step "Installing Python dependencies..."
    
    cd "/home/$USER/sensor_system"
    source venv/bin/activate
    
    # Install required packages
    pip install mysql-connector-python
    pip install schedule
    pip install luma.oled
    pip install pillow
    
    print_status "Python dependencies installed"
}

# Download and configure sensor code
setup_sensor_code() {
    print_step "Setting up sensor code..."
    
    cd "/home/$USER/sensor_system"
    
    # Download the sensor code (assuming it's available via wget/curl)
    # For now, we'll create a placeholder - in reality you'd download from your repo
    if [ -f "sensor_v2.py" ]; then
        print_warning "sensor_v2.py already exists, backing up..."
        mv sensor_v2.py "sensor_v2_backup_$(date +%Y%m%d_%H%M%S).py"
    fi
    
    # Note: In a real deployment, you'd download from your repository:
    # wget https://raw.githubusercontent.com/gagesmith3/piSensor/main/sensor_v2.py
    
    print_warning "Please copy your sensor_v2.py file to /home/$USER/sensor_system/"
    print_status "Sensor code setup prepared"
}

# Create configuration file
create_config() {
    print_step "Creating configuration file..."
    
    cd "/home/$USER/sensor_system"
    
    # Create config file
    cat > config.py << EOF
# Sensor System 2.0 Configuration
# Generated by setup script on $(date)

SENSOR_CONFIG = {
    'head_name': '$HEADER_NAME',
    'sensor_pin': $SENSOR_PIN,
    'database': {
        'host': '$DB_HOST',
        'user': '$DB_USER',
        'password': '$DB_PASS',
        'database': 'iwt_db'
    }
}
EOF
    
    print_status "Configuration file created"
}

# Create systemd service
create_service() {
    print_step "Creating systemd service..."
    
    sudo tee /etc/systemd/system/sensor-system.service > /dev/null << EOF
[Unit]
Description=Sensor System 2.0
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/home/$USER/sensor_system
Environment=PATH=/home/$USER/sensor_system/venv/bin
ExecStart=/home/$USER/sensor_system/venv/bin/python sensor_v2.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable sensor-system.service
    
    print_status "Systemd service created and enabled"
}

# Test database connection
test_database() {
    print_step "Testing database connection..."
    
    cd "/home/$USER/sensor_system"
    source venv/bin/activate
    
    python3 << EOF
import mysql.connector
import sys

try:
    conn = mysql.connector.connect(
        host='$DB_HOST',
        user='$DB_USER',
        password='$DB_PASS',
        database='iwt_db',
        connection_timeout=10
    )
    print("Database connection successful!")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"Database connection failed: {e}")
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        print_status "Database connection test passed"
    else
        print_warning "Database connection test failed - check configuration"
        print_warning "The system will still install, but may not connect until database is available"
    fi
}

# Create startup script
create_startup_script() {
    print_step "Creating management scripts..."
    
    cd "/home/$USER/sensor_system"
    
    # Create start script
    cat > start_sensor.sh << 'EOF'
#!/bin/bash
echo "Starting Sensor System 2.0..."
sudo systemctl start sensor-system.service
sudo systemctl status sensor-system.service
EOF
    
    # Create stop script
    cat > stop_sensor.sh << 'EOF'
#!/bin/bash
echo "Stopping Sensor System 2.0..."
sudo systemctl stop sensor-system.service
echo "Sensor system stopped."
EOF
    
    # Create status script
    cat > status_sensor.sh << 'EOF'
#!/bin/bash
echo "Sensor System 2.0 Status:"
sudo systemctl status sensor-system.service
echo ""
echo "Recent logs:"
sudo journalctl -u sensor-system.service -n 10 --no-pager
EOF
    
    # Make scripts executable
    chmod +x start_sensor.sh stop_sensor.sh status_sensor.sh
    
    print_status "Management scripts created"
}

# Final setup instructions
show_final_instructions() {
    echo ""
    echo "=================================================="
    print_status "Installation Complete!"
    echo "=================================================="
    echo ""
    echo "Next steps:"
    echo "1. Copy your sensor_v2.py file to /home/$USER/sensor_system/"
    echo "2. Attach the Waveshare OLED HAT to the GPIO pins"
    echo "3. Connect your inductive sensor to GPIO pin $SENSOR_PIN"
    echo "4. Reboot the Pi: sudo reboot"
    echo ""
    echo "After reboot, the sensor system will start automatically."
    echo ""
    echo "Management commands:"
    echo "  Start:  /home/$USER/sensor_system/start_sensor.sh"
    echo "  Stop:   /home/$USER/sensor_system/stop_sensor.sh"  
    echo "  Status: /home/$USER/sensor_system/status_sensor.sh"
    echo ""
    echo "View logs: sudo journalctl -u sensor-system.service -f"
    echo ""
    print_warning "A reboot is recommended to ensure all changes take effect."
}

# Main installation function
main() {
    echo "Starting automated setup for Raspberry Pi Sensor System 2.0"
    echo "This script will install all dependencies and configure the system."
    echo ""
    
    get_user_config
    
    print_step "Beginning installation..."
    
    update_system
    install_system_deps
    enable_interfaces
    setup_project
    install_python_deps
    setup_sensor_code
    create_config
    create_service
    test_database
    create_startup_script
    
    show_final_instructions
}

# Run main installation
main "$@"