import { h, Component } from 'preact';
import style from './style';

export default class ChatInput extends Component {
    onKeyDown = e => {
        let msgBody = e.target.value.trim();
        if (e.which === 13) {
            e.target.value = ''
            if (msgBody) {
                const message = {
                    roomId: this.props.roomId,
                    sender: this.props.sender,
                    body: msgBody,
                    inputType: 'text'
                }
                this.props.socket.emit('/message', message);
            }
        }
    }

    render() {
        return (
            <input class={style.chatInput} placeholder="Type here..." onKeyDown={this.onKeyDown}/>
        )
    }
}
