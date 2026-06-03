#!/bin/bash

# Inky Frame Watch and Upload Script
# Watches local directory for changes and uploads to device

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEVICE_PORT=""
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXCLUDE_PATTERNS=".git|.venv|__pycache__|.pyc|typings|.ruff_cache|build|watch_and_upload.sh"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Retry function with exponential backoff
retry_with_backoff() {
    local max_attempts=$1
    local base_delay=$2
    shift 2
    local command=("$@")
    
    local attempt=1
    local delay=$base_delay
    
    while [ $attempt -le $max_attempts ]; do
        if "${command[@]}" < /dev/null; then
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            log_warning "Attempt $attempt/$max_attempts failed, retrying in ${delay}s..."
            sleep $delay
            delay=$((delay * 2))
        fi
        
        attempt=$((attempt + 1))
    done
    
    log_error "All $max_attempts attempts failed"
    return 1
}

# Check if fswatch is installed
check_fswatch() {
    if ! command -v fswatch &> /dev/null; then
        log_error "fswatch is not installed. Install it with: brew install fswatch"
        exit 1
    fi
}

# Detect and connect to device
detect_device() {
    log_info "Detecting Inky Frame device..."
    
    # List available serial ports and find MicroPython Board (exclude Adafruit devices)
    DEVICE_PORT=$(mpremote devs 2>&1 | grep "MicroPython Board" | grep -v "Adafruit" | grep -o '/dev/\(tty\|cu\)[^ ]*' | head -n 1)
    
    if [ -z "$DEVICE_PORT" ]; then
        log_error "No MicroPython Board found. Please connect your Inky Frame and ensure it's in USB mode."
        log_error "Available devices:"
        mpremote devs 2>&1
        exit 1
    fi
    
    log_success "Device found at: $DEVICE_PORT"
}

# Stop any running program on device
stop_running_program() {
    log_info "Stopping any running program on device..."
    
    # Use reset command to stop running program with retry
    retry_with_backoff 3 1 mpremote connect "$DEVICE_PORT" reset 2>&1 || true
    sleep 2
    
    log_success "Program stopped"
}

# Upload a single file to device
upload_file() {
    local file_path=$1
    local relative_path=${file_path#$PROJECT_DIR/}
    
    # Skip excluded patterns
    for pattern in $(echo $EXCLUDE_PATTERNS | tr '|' ' '); do
        if [[ "$relative_path" == *"$pattern"* ]]; then
            return
        fi
    done
    
    # Only upload Python files and config files
    if [[ "$file_path" == *.py ]] || [[ "$file_path" == *.json ]] || [[ "$(basename "$file_path")" == "secrets.py" ]]; then
        log_info "Uploading: $relative_path"
        
        # Determine target path on device
        local target_path=":$relative_path"
        
        # Upload file with retry
        if retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp "$file_path" "$target_path" 2>&1; then
            log_success "Uploaded: $relative_path"
            sleep 1
        else
            log_error "Failed to upload: $relative_path"
            sleep 1
        fi
    fi
}

# Run main.py on device
run_main() {
    log_info "Running main.py on device..."
    
    # Wait a bit before starting to ensure device is ready
    sleep 1
    
    # Run main.py in the background
    mpremote connect "$DEVICE_PORT" run main.py &
    MPREMOTE_PID=$!
    
    log_success "main.py started (PID: $MPREMOTE_PID)"
    echo $MPREMOTE_PID > /tmp/inky_frame_mpremote.pid
}

# Initial upload of all project files
initial_upload() {
    log_info "Performing initial upload of project files..."
    
    # Upload main.py
    log_info "Uploading main.py..."
    retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp "$PROJECT_DIR/main.py" :main.py
    sleep 1
    
    # Upload core directory
    if [ -d "$PROJECT_DIR/core" ]; then
        log_info "Uploading core/ directory..."
        retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp -r "$PROJECT_DIR/core" :core
        sleep 1
    fi
    
    # Upload apps directory
    if [ -d "$PROJECT_DIR/apps" ]; then
        log_info "Uploading apps/ directory..."
        retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp -r "$PROJECT_DIR/apps" :apps
        sleep 1
    fi
    
    # Upload models directory
    if [ -d "$PROJECT_DIR/models" ]; then
        log_info "Uploading models/ directory..."
        retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp -r "$PROJECT_DIR/models" :models
        sleep 1
    fi
    
    # Upload utils directory
    if [ -d "$PROJECT_DIR/utils" ]; then
        log_info "Uploading utils/ directory..."
        retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp -r "$PROJECT_DIR/utils" :utils
        sleep 1
    fi
    
    # Upload services directory
    if [ -d "$PROJECT_DIR/services" ]; then
        log_info "Uploading services/ directory..."
        retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp -r "$PROJECT_DIR/services" :services
        sleep 1
    fi
    
    # Upload secrets.py
    if [ -f "$PROJECT_DIR/secrets.py" ]; then
        log_info "Uploading secrets.py..."
        retry_with_backoff 5 1 mpremote connect "$DEVICE_PORT" cp "$PROJECT_DIR/secrets.py" :secrets.py
        sleep 1
    fi
    
    log_success "Initial upload complete"
}

# Watch for file changes
watch_changes() {
    log_info "Watching for file changes in $PROJECT_DIR"
    log_info "Press Ctrl+C to stop"
    
    # Watch for changes in Python files and config files
    fswatch -o -r "$PROJECT_DIR" \
        --exclude=".git" \
        --exclude=".venv" \
        --exclude="__pycache__" \
        --exclude=".pyc" \
        --exclude="typings" \
        --exclude=".ruff_cache" \
        --exclude="build" \
        --exclude="watch_and_upload.sh" \
        --event=Updated \
        --event=Created \
        --event=Removed \
        | while read event; do
            # Get the changed file
            CHANGED_FILE=$(fswatch -1 -r "$PROJECT_DIR" \
                --exclude=".git" \
                --exclude=".venv" \
                --exclude="__pycache__" \
                --exclude=".pyc" \
                --exclude="typings" \
                --exclude=".ruff_cache" \
                --exclude="build" \
                --exclude="watch_and_upload.sh" \
                --event=Updated \
                --event=Created \
                --event=Removed)
            
            if [ -n "$CHANGED_FILE" ]; then
                log_info "Change detected: ${CHANGED_FILE#$PROJECT_DIR/}"
                
                # Stop running program
                stop_running_program
                
                # Upload changed file
                upload_file "$CHANGED_FILE"
                
                # Restart main.py
                run_main
            fi
        done
}

# Cleanup on exit
cleanup() {
    log_info "Cleaning up..."
    
    # Kill mpremote process if running
    if [ -f /tmp/inky_frame_mpremote.pid ]; then
        PID=$(cat /tmp/inky_frame_mpremote.pid)
        if kill -0 $PID 2>/dev/null; then
            log_info "Stopping mpremote process (PID: $PID)"
            kill $PID
            sleep 1
        fi
        rm /tmp/inky_frame_mpremote.pid
    fi
    
    # Stop program on device
    stop_running_program
    
    log_success "Cleanup complete"
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    log_info "=== Inky Frame Watch and Upload Script ==="
    
    # Check dependencies
    check_fswatch
    
    # Detect device
    detect_device
    
    # Stop any running program
    stop_running_program
    
    # Initial upload
    initial_upload
    
    # Run main.py
    run_main
    
    # Watch for changes
    watch_changes
}

# Run main function
main
