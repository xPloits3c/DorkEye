#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "  ___  "
echo " __H__    DorkEye v4.1 Setup"
echo "  [,]  "
echo "  [)]  "
echo "  [;]    Setting up environment..."
echo "  |_|  "
echo "   V   "
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}[!] Do not run this script as root!${NC}"
    exit 1
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo -e "${RED}[!] Unsupported operating system${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Detected OS: $OS${NC}"

# Check Python version
echo -e "${BLUE}[*] Checking Python version...${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[!] Python not found. Please install Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}[!] Python 3.9 or higher is required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Python $PYTHON_VERSION found${NC}"

# Install system dependencies
echo -e "${BLUE}[*] Installing system dependencies...${NC}"

if [ "$OS" == "linux" ]; then
    if command -v apt-get &> /dev/null; then
        echo -e "${YELLOW}[~] Installing via apt-get...${NC}"
        sudo apt-get update
        sudo apt-get install -y python3-pip python3-venv python3-dev build-essential libssl-dev libffi-dev
    elif command -v yum &> /dev/null; then
        echo -e "${YELLOW}[~] Installing via yum...${NC}"
        sudo yum install -y python3-pip python3-devel gcc openssl-devel
    elif command -v pacman &> /dev/null; then
        echo -e "${YELLOW}[~] Installing via pacman...${NC}"
        sudo pacman -Sy --noconfirm python-pip base-devel
    else
        echo -e "${YELLOW}[!] Unknown package manager. Please install python3-pip and python3-venv manually${NC}"
    fi
elif [ "$OS" == "macos" ]; then
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}[!] Homebrew not found. Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    echo -e "${YELLOW}[~] Installing via Homebrew...${NC}"
    brew install python3
fi

# Create virtual environment
VENV_DIR="dorkeye_env"

if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[!] Virtual environment already exists. Removing...${NC}"
    rm -rf "$VENV_DIR"
fi

echo -e "${BLUE}[*] Creating virtual environment...${NC}"
$PYTHON_CMD -m venv "$VENV_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}[!] Failed to create virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Virtual environment created successfully${NC}"

# Activate virtual environment
echo -e "${BLUE}[*] Activating virtual environment...${NC}"

# Source the activation script
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    echo -e "${GREEN}[✓] Virtual environment activated${NC}"
else
    echo -e "${RED}[!] Activation script not found${NC}"
    exit 1
fi

# Verify we're in the virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}[!] Failed to activate virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Currently using: $(which python)${NC}"

# Upgrade pip
echo -e "${BLUE}[*] Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}[*] Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[✓] All dependencies installed successfully${NC}"
    else
        echo -e "${RED}[!] Failed to install some dependencies${NC}"
        exit 1
    fi
else
    echo -e "${RED}[!] requirements.txt not found${NC}"
    exit 1
fi

# Make dorkeye.py executable
if [ -f "dorkeye.py" ]; then
    chmod +x dorkeye.py
    echo -e "${GREEN}[✓] Made dorkeye.py executable${NC}"
fi

# Create activation helper script
cat > activate_dorkeye.sh << 'EOF'
#!/bin/bash
source dorkeye_env/bin/activate
echo -e "\033[0;32m[✓] DorkEye virtual environment activated\033[0m"
echo -e "\033[0;34m[*] Run: python dorkeye.py -h for help\033[0m"
EOF

chmod +x activate_dorkeye.sh

# Summary
echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}[✓] Setup completed successfully!${NC}"
echo -e "${RED}[*] The dork sees all!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "${YELLOW}1. Create and activate the virtual environment manually:${NC}"
echo -e "   ${GREEN}python3 -m venv dorkeye_env${NC}"
echo -e "   ${GREEN}source dorkeye_env/bin/activate${NC}"
echo -e "   ${YELLOW}or use:${NC} ${GREEN}source activate_dorkeye.sh${NC}\n"

echo -e "${YELLOW}2. Run DorkEye:${NC}"
echo -e "   ${GREEN}python dorkeye.py -h${NC}\n"

echo -e "${YELLOW}3. Example usage:${NC}"
echo -e "   ${GREEN}python dorkeye.py -d \"site:example.com filetype:pdf\" -o results${NC}"
echo -e "   ${GREEN}python dorkeye.py -d dorks.txt -o output --sqli${NC}\n"

echo -e "${BLUE}[*] To deactivate: ${GREEN}deactivate${NC}\n"

# Keep the virtual environment active for the user
echo -e "${YELLOW}[*] Virtual environment is active in this session${NC}"
echo -e "${YELLOW}[*] Open a new terminal or source activate_dorkeye.sh to use DorkEye${NC}\n"

# S
