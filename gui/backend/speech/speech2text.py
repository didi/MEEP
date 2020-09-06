
"""Google Cloud Speech API sample application using the REST API for batch
processing.

Example usage:
    python transcribe.py resources/audio.raw
    python transcribe.py gs://cloud-samples-tests/speech/brooklyn.flac
"""

import argparse
from google.cloud import speech_v1
from google.cloud.speech import enums
from google.cloud.speech import types
import io
import os
from google.oauth2 import service_account
from keys import keys


def backend_process(content, language_code):
    credentials_file = keys['google_speech']
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file)
    client = speech_v1.SpeechClient(credentials=credentials)
    transcribe_result = transcribe_file(content, client, language_code)
    return transcribe_result


def read_audio_file(input_file_path):
    """
    Args:
    input_file_path:
    :return:
    content:       binary audio cpntent
    """
    with io.open(input_file_path, 'rb') as audio_file:
        content = audio_file.read()

    return content

# [START speech_transcribe_sync]


def transcribe_file(content, client, language_code):
    """
    Transcribe the given audio file.
    Args:
    content:    binary audio content
    client:     client instance
    params:       hparams
    :returns
    transcribe_result   string of transcribed content
    """
    # [START speech_python_migration_sync_request]
    # [START speech_python_migration_config]

    audio = types.RecognitionAudio(content=content)
    config = types.RecognitionConfig(
        audio_channel_count=2,
        enable_separate_recognition_per_channel=True,
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code=language_code)
    # [END speech_python_migration_config]

    # [START speech_python_migration_sync_response]

    response = client.recognize(config, audio)

    # [END speech_python_migration_sync_request]
    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.

    tmp_transcribe_result = ""
    for result in response.results:
        # First alternative is the most probable result
        alternative = result.alternatives[0]
        print(u"Transcript: {}".format(alternative.transcript))
        tmp_transcribe_result = alternative.transcript
    # [END speech_python_migration_sync_response]

    transcribe_result = tmp_transcribe_result
    # print(f"transcribe_result :{transcribe_result }")

    return transcribe_result

# [END speech_transcribe_sync]
# [START speech_transcribe_sync_gcs]


def transcribe_gcs(gcs_uri):
    """Transcribes the audio file specified by the gcs_uri."""
    client = speech.SpeechClient()

    # [START speech_python_migration_config_gcs]
    audio = types.RecognitionAudio(uri=gcs_uri)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
        language_code='en-US')
    # [END speech_python_migration_config_gcs]

    response = client.recognize(config, audio)
    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    for result in response.results:
        # The first alternative is the most likely one for this portion.
        print(u'Transcript: {}'.format(result.alternatives[0].transcript))
# [END speech_transcribe_sync_gcs]


def save_transcibe2file(transcribe_content,
                        output_dir,
                        output_file_name="transcribe_content.txt"):
    """

    :return:
    """
    output_path = os.path.join(output_dir, output_file_name)

    with open(output_path, 'w') as out:
        # Write the response to the output file.
        out.write(transcribe_content)
        # print(f'transcribe content written to file {output_path}')


def get_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--input',
        help='File or GCS path for audio file to be recognized')
    parser.add_argument('--service', help='service_account.json')
    parser.add_argument(
        "--output_dir",
        default="./output/",
        help='dir to save audio file returned')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = get_args()

    # set up client instance
    credentials = service_account.Credentials.from_service_account_file(
        os.path.abspath(args.service))
    client = speech.SpeechClient(credentials=credentials)

    # read audio file
    audio_content = read_audio_file(args.input)

    transcribe_result = transcribe_file(content=audio_content,
                                        client=client)

    # print(f"transcribe_result: {transcribe_result}")

    # write transcribe_result to disk
    if args.output_dir:
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        # extract /root/dir/sub/file.ext.zip -> file.ext
        filename = os.path.splitext(os.path.basename(os.path.abspath(args.input)))[
            0] + "_transcribe_content.txt"
        save_transcibe2file(transcribe_content=transcribe_result,
                            output_dir=args.output_dir,
                            output_file_name=filename)
