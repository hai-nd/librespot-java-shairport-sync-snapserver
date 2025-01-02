#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Work successfully!

import os
import sys
import re
import signal
import requests
import threading
import json
import base64
from subprocess import Popen, PIPE

# Spotify API credentials
CLIENT_ID = "put-your-client_id-here"
CLIENT_SECRET = "put-your-client_secret-here"

# Paths
LIBRESPOT_API_JAR = "librespot-api-1.6.3.jar"
LIBRESPOT_DIR = "/usr/local/bin"
METADATA_PIPE = "/tmp/librespot-java.metadata"

# Global process reference
librespot_process = None


# Signal handler for clean exit
def signal_handler(sig, frame):
    global librespot_process
    if librespot_process:
        print("Stopping librespot process...", file=sys.stderr)
        librespot_process.terminate()
        librespot_process.wait()
    sys.exit(0)


# Fetch Spotify API token
def get_spotify_token(client_id, client_secret):
    try:
        url = "https://accounts.spotify.com/api/token"
        auth_header = {
            "Authorization": f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}"
        }
        payload = {"grant_type": "client_credentials"}
        response = requests.post(url, headers=auth_header, data=payload)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except Exception as e:
        print(f"Error fetching Spotify token: {e}", file=sys.stderr)
        return None


# Start the librespot-java process
def start_librespot(access_token):
    global librespot_process
    try:
        print("Starting librespot process...", file=sys.stderr)
        os.chdir(LIBRESPOT_DIR)
        command = [
            "java",
            "-jar",
            LIBRESPOT_API_JAR,
            "--verbose",
            f"--token={access_token}",
            f"--metadataPipe={METADATA_PIPE}"
        ]
        librespot_process = Popen(command, stdout=PIPE, stderr=PIPE, text=True)

        # Log stderr in a separate thread
        threading.Thread(target=log_librespot_output, args=(librespot_process.stderr,), daemon=True).start()
    except Exception as e:
        print(f"Error starting librespot process: {e}", file=sys.stderr)

# Log librespot stderr for useful metadata
def log_librespot_output(stderr):
    """
    Reads the stderr output from librespot-java and processes metadata.
    """
    try:
        for line in stderr:
            print(f"Raw log line: {line.strip()}", file=sys.stderr)  # Debugging log lines
            if "Loaded track" in line:
                process_metadata_from_log(line)
    except Exception as e:
        print(f"Error reading librespot log: {e}", file=sys.stderr)


# Process metadata from librespot log
def process_metadata_from_log(log_line):
    """
    Extract and transform track metadata from librespot log, fetch album art, and send to Snapserver.
    """
    try:
        if "Loaded track" in log_line:
            # Extract raw metadata
            start_idx = log_line.find("{")
            end_idx = log_line.rfind("}")
            if start_idx != -1 and end_idx != -1:
                raw_metadata = log_line[start_idx:end_idx + 1]

                # Parse the raw metadata using a regex-based approach
                metadata_dict = parse_raw_metadata(raw_metadata)

                if not metadata_dict:
                    print(f"Failed to parse metadata: {raw_metadata}", file=sys.stderr)
                    return

                # Transform metadata to the required format
                title = metadata_dict.get("name", "Unknown Title")
                artists = [metadata_dict.get("artists", "Unknown Artist")]  # Convert to a list
                duration_ms = metadata_dict.get("duration", 0)
                duration = round(duration_ms / 1000, 1)  # Convert to seconds as a float
                track_uri = metadata_dict.get("uri", "")
                track_id = metadata_dict.get("id", "")
                art_url = get_album_art(track_uri) if track_uri else None

                # Create the transformed metadata dictionary
                transformed_metadata = {
                    "title": title,
                    "artist": artists,
                    "duration": duration,
                    "artUrl": art_url,
                }

                # Send transformed metadata to Snapserver
                send_transformed_metadata_to_snapserver(transformed_metadata)
            else:
                print("No valid JSON object found in log line.", file=sys.stderr)
    except Exception as e:
        print(f"Error processing metadata from log: {e}", file=sys.stderr)

# Parse raw metadata into a dictionary
def parse_raw_metadata(raw_metadata):
    """
    Parse the raw metadata string (not valid JSON) into a proper Python dictionary.
    """
    try:
        # Use regex to extract key-value pairs from the raw metadata
        pattern = r"(\w+):\s*'([^']*)'|(\w+):\s*([\d.]+)|(\w+):\s*([^,\s]+)"
        matches = re.findall(pattern, raw_metadata)

        metadata_dict = {}
        for match in matches:
            key = match[0] or match[2] or match[4]
            value = match[1] or match[3] or match[5]

            # Convert numeric values to int/float
            if value.isdigit():
                value = int(value)
            elif re.match(r"^\d+\.\d+$", value):  # Check for floats
                value = float(value)

            metadata_dict[key] = value

        return metadata_dict
    except Exception as e:
        print(f"Error parsing raw metadata: {e}", file=sys.stderr)
        return None

# Get album art URL from Spotify API
def get_album_art(track_uri):
    """
    Fetch album art URL using the Spotify API and the track URI.
    """
    try:
        track_id = track_uri.split(":")[-1]  # Extract track ID from the URI
        access_token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)  # Ensure valid Spotify API token
        if not access_token:
            return None

        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        track_data = response.json()

        # Extract the largest album art image URL
        return track_data["album"]["images"][0]["url"]
    except Exception as e:
        print(f"Error fetching album art: {e}", file=sys.stderr)
        return None

# Send transformed metadata to Snapserver
def send_transformed_metadata_to_snapserver(metadata):
    """
    Send transformed metadata to Snapserver in the required format.
    """
    try:
        message = {
            "jsonrpc": "2.0",
            "method": "Plugin.Stream.Player.Properties",
            "params": {
                "playbackStatus": "playing",
                "metadata": metadata
            }
        }
        print(f"Sending transformed metadata: {json.dumps(message, indent=4)}", file=sys.stderr)  # Debug message
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error sending transformed metadata to Snapserver: {e}", file=sys.stderr)

# Main function
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)
    if not token:
        print("Failed to fetch Spotify token. Exiting...", file=sys.stderr)
        sys.exit(1)

    start_librespot(token)

    try:
        while True:
            signal.pause()
    except KeyboardInterrupt:
        pass