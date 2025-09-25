# translate_data.py
import os
import json
import argparse
from google.cloud import translate_v2 as translate

# --- Configuration ---
# Path to your downloaded service account key file
# Make sure this file is in the same directory as this script or provide the full path
CREDENTIALS_FILE = "google-credentials.json"

def translate_text(client, text, target_language):
    """Helper function to translate a single piece of text."""
    if not text:
        return ""
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
        print(f"  Error translating text: {e}")
        return f"[Translation Error: {str(e)}]" # Or return original text

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
    translated_count = 0
    for i, entry in enumerate(data):
        print(f"Processing entry {i+1}/{len(data)}: {entry.get('url', 'N/A')}")
        original_title = entry.get('title', '')
        original_description = entry.get('description', '')

        # Translate Title
        if original_title:
            translated_title_key = f"translated_title_{target_language_code}"
            entry[translated_title_key] = translate_text(translate_client, original_title, target_language_code)
            translated_count += 1

        # Translate Description
        if original_description:
            translated_desc_key = f"translated_description_{target_language_code}"
            entry[translated_desc_key] = translate_text(translate_client, original_description, target_language_code)
            translated_count += 1

    print(f"\nTranslation process completed. Total fields translated: {translated_count}")

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
      
