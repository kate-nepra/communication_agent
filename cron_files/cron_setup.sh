#!/bin/bash

# Path to the directory containing all the files
FILES_DIR="/"

# Cron job for cron_event.sh - runs daily at midnight
echo "0 0 * * * bash $FILES_DIR/cron_event.sh" > /etc/cron.d/cron_event

# Cron job for cron_administration.sh - runs weekly on Mondays at midnight
echo "0 0 * * 1 bash $FILES_DIR/cron_administration.sh" > /etc/cron.d/cron_administration

# Cron job for cron_place.sh - runs monthly on the 1st day of the month at midnight
echo "0 0 1 * * bash $FILES_DIR/cron_place.sh" > /etc/cron.d/cron_place

# Cron job for cron_static.sh - runs semi-annually on 1st January and 1st July at midnight
echo "0 0 1 1,7 * bash $FILES_DIR/cron_static.sh" > /etc/cron.d/cron_static

# Cron job for cron_pdf.sh - runs yearly on 1st November at midnight (New Gourmet pdf is released in October)
echo "0 0 1 11 * bash $FILES_DIR/cron_pdf.sh" > /etc/cron.d/cron_pdf