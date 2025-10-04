# translate_data.py
import os
import json
import argparse
import time
import random
from google.cloud import translate_v2 as translate

# --- Configuration ---
# Path to your downloaded service account key file
# Make sure this file is in the same directory as this script or provide the full path
CREDENTIALS_FILE = "google-credentials.json"

# --- Retry Configuration ---
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds
MAX_DELAY = 60  # seconds
BACKOFF_FACTOR = 2

def translate_text(client, text, target_language):
    """Helper function to translate a single piece of text with retry logic."""
    if not text:
        return ""

    for attempt in range(MAX_RETRIES):
        try:
            # Detect source language automatically
            detection_result = client.detect_language(text)
            source_lang = detection_result['language']
            print(f"  Detected source language: {source_lang}")

            # Perform translation
            translation_result = client.translate(
                text,
                target_language=target_language,
                source_language=source_lang # Providing source improves accuracy
            )
            translated_text = translation_result['translatedText']
            print(f"  Translated: '{text[:50]}...' -> '{translated_text[:50]}...'")
            return translated_text

        except Exception as e:
            error_msg = str(e).lower()
            print(f"  Error translating text (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

            # Check if it's a rate limit error (429) or server error (5xx)
            if any(code in error_msg for code in ['429', 'rate limit', 'quota exceeded']) or \
               (hasattr(e, 'code') and e.code >= 500):
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff with jitter
                    delay = min(BASE_DELAY * (BACKOFF_FACTOR ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    print(f"  Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    print("  Max retries exceeded for rate limit error")
                    return f"[Rate Limit Error: {str(e)}]"
            else:
                # For other errors (auth, invalid input, etc.), don't retry
                return f"[Translation Error: {str(e)}]"

    # If we get here, all retries failed
    return f"[Translation Failed after {MAX_RETRIES} attempts]"

def main(input_file_path, target_language_code, output_file_path=None):
    """
    Main function to translate data.
    Args:
        input_file_path (str): Path to the input JSON file (e.g., 'data.json').
        target_language_code (str): Target language code (e.g., 'bn' for Bangla).
        output_file_path (str, optional): Path for the output JSON file.
                                          Defaults to inserting '_translated_{lang}' before '.json'.
    """
    # 1. Set up Google Translate Client
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_FILE
        translate_client = translate.Client()
        print(f"Successfully initialized Google Translate client using {CREDENTIALS_FILE}")
    except Exception as e:
        print(f"Failed to initialize Google Translate client: {e}")
        print("Please ensure:")
        print("1. 'google-credentials.json' is in the correct location.")
        print("2. The GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly (handled by this script).")
        print("3. The 'google-cloud-translate' library is installed in your environment.")
        return

    # 2. Determine Output File Path
    if not output_file_path:
        base_name, ext = os.path.splitext(input_file_path)
        output_file_path = f"{base_name}_translated_{target_language_code}{ext}"
    print(f"Input file: {input_file_path}")
    print(f"Target language: {target_language_code}")
    print(f"Output file: {output_file_path}")

    # 3. Load Data
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded {len(data)} entries from {input_file_path}")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file_path}' not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from '{input_file_path}': {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return

    # 4. Translate Data
    print("\nStarting translation process...")
    print(f"Processing {len(data)} entries...")

    translated_count = 0
    failed_count = 0
    start_time = time.time()

    for i, entry in enumerate(data):
        if (i + 1) % 10 == 0 or i == 0:  # Progress update every 10 entries
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  Progress: {i+1}/{len(data)} ({rate:.1f} entries/sec)")

        url = entry.get('url', 'N/A')
        print(f"  Processing entry {i+1}: {url}")

        original_title = entry.get('title', '')
        original_description = entry.get('description', '')

        # Translate Title
        if original_title and original_title.strip():
            translated_title_key = f"translated_title_{target_language_code}"
            translated_title = translate_text(translate_client, original_title, target_language_code)
            if not translated_title.startswith('['):  # Check if translation was successful
                entry[translated_title_key] = translated_title
                translated_count += 1
            else:
                failed_count += 1
                print(f"    Title translation failed: {translated_title}")

        # Translate Description
        if original_description and original_description.strip():
            translated_desc_key = f"translated_description_{target_language_code}"
            translated_desc = translate_text(translate_client, original_description, target_language_code)
            if not translated_desc.startswith('['):  # Check if translation was successful
                entry[translated_desc_key] = translated_desc
                translated_count += 1
            else:
                failed_count += 1
                print(f"    Description translation failed: {translated_desc}")

    elapsed_time = time.time() - start_time
    print("
Translation process completed!")
    print(f"  Total entries processed: {len(data)}")
    print(f"  Successful translations: {translated_count}")
    print(f"  Failed translations: {failed_count}")
    print(f"  Processing time: {elapsed_time:.1f} seconds")
    print(f"  Average rate: {len(data)/elapsed_time:.1f} entries/sec")

    # 5. Save Translated Data
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False) # ensure_ascii=False preserves Unicode
        print(f"Successfully saved translated data to {output_file_path}")
    except Exception as e:
        print(f"Error saving translated data to '{output_file_path}': {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Translate titles and descriptions in a Nirobo data JSON file."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input JSON file (e.g., data.json)"
    )
    parser.add_argument(
        "target_language",
        help="Target language code (e.g., bn for Bangla, es for Spanish)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Path for the output JSON file (default: input_translated_{lang}.json)"
    )

    args = parser.parse_args()

    main(args.input_file, args.target_language, args.output)
      
