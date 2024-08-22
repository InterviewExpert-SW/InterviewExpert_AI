from flask import Flask, request, jsonify, send_file
import azure.cognitiveservices.speech as speechsdk
import requests
import os

app = Flask(__name__)

#인식 파트
def recognize_speech_from_wav(wav_data):
    subscription_key = ""
    service_region = ""

    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=service_region)
    audio_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)

    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    audio_stream.write(wav_data)
    audio_stream.close()

    result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognized."
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_message = f"Speech Recognition canceled: {cancellation_details.reason}"
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            error_message += f"\nError details: {cancellation_details.error_details}"
        raise Exception(error_message)

    return None


#챗봇 파트
def call_chatbot_api(text):
    api_url = ""
    headers = {
        "Authorization": f"",
        "Content-Type": "application/json"
    }
    data = {
    "model": "YOUR_MODEL_NAME",  # 파인튜닝된 모델 이름
    "prompt": "면접관 입장에서 지원자에게 질문을 하는 역할. user가 말하는 내용을 듣고, 추가적인 꼬리질문을 해야 한다.",  # 실제 프롬프트 텍스트
    "max_tokens": 100,
    "temperature": 1.0
    }

    response = requests.post(api_url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["text"].strip()
    else:
        raise Exception("Error: Unable to get a response from the chatbot.")


#tts 파트
def azure_text_to_speech(text):
    subscription_key = ""
    service_region = ""
    output_filename = "output.wav"

    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=service_region)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_filename)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesized and saved to {output_filename}.")
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
        raise Exception("Speech synthesis failed.")
    
    return output_filename

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    # Step 1: Get the audio data from the request
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file provided"}), 400
    
    wav_data = file.read()

    # Step 2: Recognize speech (STT)
    try:
        recognized_text = recognize_speech_from_wav(wav_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Step 3: Call chatbot API to get response
    try:
        chatbot_response = call_chatbot_api(recognized_text)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Step 4: Convert chatbot response to speech (TTS)
    try:
        output_filename = azure_text_to_speech(chatbot_response)
        return send_file(output_filename, mimetype='audio/wav', as_attachment=True, download_name='output.wav')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(output_filename):
            os.remove(output_filename)

if __name__ == '__main__':
    app.run(debug=True)
