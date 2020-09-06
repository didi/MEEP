import { h, Component, createRef } from 'preact';
import style from './style';

import ChatMessage from "../../components/chat_message/index";
const newMessageSound = new Audio('/me-too.mp3')

export default class ChatWindow extends Component {
    state = {
        messages: [],
        queuedMessages: []
    };
    messagesEndRef = createRef()

    constructor(props) {
        super(props);
    }

    componentWillReceiveProps(newProps) {
        this.setState({
            queuedMessages: newProps.queuedMessages
        });
    }

    // Originates a new message
    newSystemMessage = (message) => {
        message = {roomId: this.props.roomId, template: '', variables: [], ...message};
        this.props.socket.emit('/message', message);
        this.appendMessage(message);
    }

    // Display a message from history or one that has been received
    appendMessage = (message) => {
        let messages = this.state.messages;
        messages.push({roomId: this.props.roomId, ...message});
        this.setState({ messages });
    }

    scrollToBottom = () => {
        this.messagesEndRef.current.scrollIntoView({behaviour: 'smooth'});
    }

    componentDidMount () {
        this.props.socket.on('/history/messages', (data) => {
            this.state.messages = [];
            data.forEach(this.appendMessage);
        });
        this.props.socket.on('/message', (message) => {
            this.appendMessage(message);
            newMessageSound.play();
        });

        this.props.socket.on('/end_dialog', (data) => {
            if (!data.success) {
                // This is triggered if the agent selects give up
                this.socket.emit('/end_dialog_confirm', {
                    correct: false,
                    roomId: this.props.roomId
                });
                this.newSystemMessage({sender: 'system', body: `
                    The agent has ended the dialog.
                    Logs have been saved to ${data.filename}
                    `}
                )

                // TODO: move to the next dialog
            }
            else if (data.success) {
                const end_dialog_options = [{
                        text: 'Yes',
                        socketEvent: '/end_dialog_confirm',
                        correct: true,
                    },
                    {
                        text: 'No',
                        socketEvent: '/end_dialog_confirm',
                        correct: false,
                    }];

                // Show data for the user to confirm
                switch (data.confirmationType) {
                    // If the user selects start_driving, the system will display a map for the user to confirm the location
                    case 'map':
                        const lat = data.data[0].value;
                        const lon = data.data[1].value;
                        const destID = data.data[2].value;
                        let body;
                        if (destID !== 'undefined') { // this value is from add_adjacent_variable
                            body = (<iframe height="450" frameborder="0" style="border:0;width:100%" src={
                                `https://www.google.com/maps/embed/v1/place?q=place_id:${destID}&key=${process.env.GMAP_EMBED_KEY}`} allowfullscreen>
                            </iframe>)
                        }
                        else {
                            body = (<iframe height="450" frameborder="0" style="border:0;width:100%" src={
                                `https://www.google.com/maps/embed/v1/place?q=${lat},${lon}&key=${process.env.GMAP_EMBED_KEY}`} allowfullscreen>
                            </iframe>)
                        }
                        this.newSystemMessage({sender: 'system', body});
                        this.newSystemMessage({
                            sender: 'system',
                            body: 'The agent has selected the place above as your destination. Is that correct?',
                            options: end_dialog_options
                        })
                        break;

                    // Default: yes/ no satisfaction question
                    case 'rate_satisfaction':
                        this.newSystemMessage({
                            sender: 'system',
                            body: 'The agent has ended the dialog. Were you satisfied?',
                            options: end_dialog_options
                        })
                        break;

                    // Custom string
                    case 'confirm_information':
                        const confirmationString = data.data[data.data.length - 1].value;
                        this.newSystemMessage({sender: 'system', body: confirmationString, options: end_dialog_options})
                        break;

                    default:
                        this.newSystemMessage({sender: 'system', body: JSON.stringify(data.data), options: end_dialog_options})
                }

                if (data.endHint) {
                    this.newSystemMessage({
                        sender: 'system',
                        body: `The destination should be ${endHint}`
                    });
                }

                if (data.filename) {
                    this.newSystemMessage({sender: 'system', body: 'Logs were successfully saved'});
                    console.log(`Logs were saved to ${data.filename}`);
                }
            }
        })

        this.props.socket.on('/play_audio', (audio) => {
            if (this.props.speech) {
                var blob = new Blob([audio], { type: 'audio/mp3' })
                var url = window.URL.createObjectURL(blob)
                audio = document.getElementById("audioPlayer");
                audio.src = url;
                audio.loop = false;
                audio.play()
            }
        });

        if (!this.props.speech) this.scrollToBottom();
    }

    // This should probably be factored out into a separate react component, and room_id and socket should be added to redux
    showMessageOptions = (option) => {
        return (<li class={style.confirmButton} onclick={() => this.props.socket.emit(option.socketEvent, {roomId: this.props.roomId, correct: option.correct})}>{option.text}</li>);
    }

    componentDidUpdate() {
        if (!this.props.speech) this.scrollToBottom();
    }

    render(props, state) {
        if (!props.speech) {
            return (
                <div class={style.chatWindow}>
                    <ul class={style.chatMessages}>
                        {
                            state.messages.map(message => {
                                let content;
                                if ('target_language' in message) {
                                    content = message.target_language === props.displayLanguage ? message.translated_body : message.body;
                                } else {
                                    content = message.body;
                                }
                                let dropdown_events = "breakdown_events" in message ? message.breakdown_events : null;
                                let relative_sender;
                                if (message.sender === 'system') {
                                    relative_sender = 'system';
                                }
                                else if (message.sender === props.sender) {
                                    relative_sender = 'me';
                                }
                                else if (message.sender !== props.sender) {
                                    relative_sender = 'them';
                                }
                                return (<ChatMessage 
                                    key={message.id}
                                    roomId={this.props.roomId}
                                    id={message.id}
                                    dropdown_indices_and_lengths={[]}
                                    sender={relative_sender}
                                    body={content}
                                    socket={this.props.socket}
                                    dropdown_events={dropdown_events}
                                    options={message.options}
                                    showMessageOptions={this.showMessageOptions}
                                />);
                            }).concat(state.queuedMessages.map(message => {
                                let content;
                                if ('target_language' in message) {
                                    content = message.target_language === props.displayLanguage ? message.translated_body : message.body;
                                } else {
                                    content = message.body;
                                }
                                return (<ChatMessage sender={'queue'} body={content}/>);
                            }))
                        }
                        <div ref={this.messagesEndRef}/>
                    </ul>
                </div>
            );
        } else {
            return (
                <audio id="audioPlayer" controls="controls" loop="false" hidden="true"></audio>
            );
        }
    }
}
