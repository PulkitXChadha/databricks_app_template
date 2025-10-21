#!/bin/bash

# View Databricks App logs with formatting and colors
# Can be used to tail existing logs or view historical logs

LOG_FILE="/tmp/databricks-app-watch.log"

# Check if format_logs.py exists
if [ ! -f "scripts/format_logs.py" ]; then
  echo "Error: scripts/format_logs.py not found"
  exit 1
fi

# Parse command line arguments
FOLLOW=false
LINES=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -f|--follow)
      FOLLOW=true
      shift
      ;;
    -n|--lines)
      LINES="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "View Databricks App logs with formatting and colors"
      echo ""
      echo "Options:"
      echo "  -f, --follow       Follow log output (like tail -f)"
      echo "  -n, --lines N      Show last N lines"
      echo "  -h, --help         Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                 View all logs"
      echo "  $0 -n 100          View last 100 lines"
      echo "  $0 -f              Follow logs in real-time"
      echo "  $0 -n 50 -f        Show last 50 lines and follow"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run '$0 --help' for usage information"
      exit 1
      ;;
  esac
done

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
  echo "⚠️  Log file not found: $LOG_FILE"
  echo "💡 Start the development servers first with: ./watch.sh"
  exit 1
fi

# Build tail command
TAIL_CMD="tail"
if [ "$FOLLOW" = true ]; then
  TAIL_CMD="$TAIL_CMD -f"
fi
if [ -n "$LINES" ]; then
  TAIL_CMD="$TAIL_CMD -n $LINES"
fi

# View logs with formatting
if [ "$FOLLOW" = true ]; then
  echo "📄 Following logs from: $LOG_FILE"
  echo "Press Ctrl+C to stop"
  echo ""
  $TAIL_CMD "$LOG_FILE" | python3 scripts/format_logs.py
else
  if [ -n "$LINES" ]; then
    echo "📄 Showing last $LINES lines from: $LOG_FILE"
  else
    echo "📄 Showing all logs from: $LOG_FILE"
  fi
  echo ""
  $TAIL_CMD "$LOG_FILE" | python3 scripts/format_logs.py
fi

