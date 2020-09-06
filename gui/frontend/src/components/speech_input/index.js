import { h, Component } from 'preact';
import style from './style';

import Recorder from 'recorder-js';

export default class SpeechInput extends Component {
    constructor(props) {
        super(props);
        this.startRecording = this.startRecording.bind(this);
        this.stopRecording = this.stopRecording.bind(this);
        this.send_audio = this.send_audio.bind(this);
        this.onMouseUp = this.onMouseUp.bind(this);
    }

    componentDidMount() {
        const audioContext =  new (window.AudioContext || window.webkitAudioContext)();
        this.recorder = new Recorder(audioContext, {
            numChannels:1
        });
        navigator.mediaDevices.getUserMedia({audio: true})
          .then(stream => this.recorder.init(stream))
          .catch(err => console.log('Uh oh... unable to get stream...', err));
        document.addEventListener('mousedown', () => audioContext.resume());
    }

    startRecording() {
      let audio = document.getElementById("recordAudio");
      audio.pause();
      this.recorder.start()
    }

    stopRecording() {
      this.recorder.stop()
        .then(({blob, buffer}) => {
            let tmp_blob = blob;
            var fd = new FormData();
            fd.append('audio', tmp_blob);
            this.send_audio(fd);
        })
    }

    onMouseUp() {
      setTimeout(this.stopRecording, 500);
    }

    async send_audio(fd) {
      const requestURL = `${process.env.SERVER_URL}:${process.env.SERVER_PORT}/speech2text`;
      let response = await fetch(requestURL, {
            method: 'POST',
            body: fd,
      });
    }

    render() {
        return (
            <div>
                <audio id="recordAudio" controls="controls" loop="false" hidden="true"></audio>
                <div onMouseDown={this.startRecording} onMouseUp={this.onMouseUp} class={style.recordButton}>
                  <div class={style.recordButtonRecording}></div>
                </div>
            </div>
        )
    }
}
