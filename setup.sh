#!/bin/bash
# setup.sh - Initialize piSensor for first run

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"
VENV_DIR="$SCRIPT_DIR/venv"

echo "========================================="
echo "  piSensor Setup"
echo "========================================="
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        echo "Creating .env from .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "✓ .env created. Please edit it with your specific configuration:"
        echo "  - HEAD_NAME: Your heading identifier"
        echo "  - HEAD_ID: Your heading ID"
        echo "  - SENSOR_PIN: GPIO pin number if different from 17"
        echo ""
        echo "Edit with: nano .env"
    else
        echo "✗ .env.example not found!"
        exit 1
    fi
else
    echo "✓ .env already exists"
fi

# Install/upgrade pip
echo ""
echo "Updating pip..."
pip install -q --upgrade pip

# Install required Python packages
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "========================================="
echo "✓ Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit your configuration: nano .env"
echo "2. Run the sensor: python3 sensor.py"
echo ""
echo "To activate the virtual environment in the future:"
echo "  source venv/bin/activate"

