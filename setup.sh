#!/bin/bash
# setup.sh - Initialize piSensor for first run

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

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
        echo "Then run: python3 sensor.py"
    else
        echo "✗ .env.example not found!"
        exit 1
    fi
else
    echo "✓ .env already exists"
fi

# Check if required Python packages are installed
echo ""
echo "Checking Python dependencies..."
python3 -m pip install -q -r requirements.txt 2>/dev/null || {
    echo "Installing Python requirements..."
    python3 -m pip install -r requirements.txt
}

echo ""
echo "✓ Setup complete! You can now run: python3 sensor.py"
