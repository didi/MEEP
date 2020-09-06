"""Synthesizes speech from the input string of text or ssml.

Note: ssml must be well-formed according to:
    https://www.w3.org/TR/speech-synthesis/
"""

import argparse

import os
from google.oauth2 import service_account
from google.cloud import texttospeech
from keys import keys


def backend_process(text, language_code):
    credentials_file = keys['google_speech']
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file)
    client = texttospeech.TextToSpeechClient(credentials=credentials)

    audio_content = text2speech(client, text, language_code)
    return audio_content


def read_text_from_file(input_file_path):
    """
    Args:
    input_file_path:
    :return:
    text:       string of text to be synthesized
    """
    with open(input_file_path, 'r') as f:
        text = f.read()
    return text


def text2speech(client, text, language_code):
    """
    Args:
    params:       hparams
    client:     client instance

    :return:
    """

    # Set the text input to be synthesized
    synthesis_input = texttospeech.types.SynthesisInput(text=text)

    # Build the voice request, select the language code and the ssml
    # voice gender ("neutral")
    voice = texttospeech.types.VoiceSelectionParams(
        language_code=language_code,
        ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL)

    # Select the type of audio file you want returned
    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = client.synthesize_speech(synthesis_input, voice, audio_config)

    # The response's audio_content is binary.
    return response.audio_content


def save_audio_file(audio_content,
                    output_dir,
                    output_file_name="output.mp3"):
    """

    :return:
    """
    output_path = os.path.join(output_dir, output_file_name)

    with open(output_path, 'wb') as out:
        # Write the response to the output file
        out.write(audio_content)


def get_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--input', help='text input file to be synthesized')
    parser.add_argument('--service', help='service_account.json')
    parser.add_argument(
        "-o",
        default="./output/",
        help='dir to save audio file returned')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = get_args()

    # Instantiates a client
    credentials = service_account.Credentials.from_service_account_file(
        os.path.abspath(args.service))
    client = texttospeech.TextToSpeechClient(credentials=credentials)

    # read text file
    text = read_text_from_file(args.input)

    #
    audio_content = text2speech(client=client, text=text)

    # save to local file
    save_audio_file(audio_content=audio_content, output_dir=args.o)
