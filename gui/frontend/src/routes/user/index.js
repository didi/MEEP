import { h, Component } from 'preact';
import style from './style';
import io from 'socket.io-client';

import ChatWindow from '../../components/chat_window/index.js';
import ChatInput from '../../components/chat_input/index.js';
import SpeechInput from '../../components/speech_input/index.js';
import ConfigPanel from './config_panel';

import { confirmAlert } from 'react-confirm-alert'; // Import
import 'react-confirm-alert/src/react-confirm-alert.css'; // Import css

export default class User extends Component {
    constructor(props) {
        super(props);
        this.roomId = props.roomId;
        this.initializeSocket();
        this.state = {
            options: {
                inputLanguage: 'en',
                inputType: 'text',
                initialVariables: {
                    'loading options': 'in progress',
                },
                evaluationProgress: {
                    currentIndex: 0,
                    total: 0
                },
                userStory: {}
            }
        };
        this.endDialog = this.endDialog.bind(this);
        this.handleOptionChange = this.handleOptionChange.bind(this);
        this.confirmOptionChange = this.confirmOptionChange.bind(this);
        this.loadOptions = this.loadOptions.bind(this);
    }

    initializeSocket = () => {
        this.socket = io(process.env.SERVER_URL + ":" + process.env.SERVER_PORT);
        this.socket.on('join_error', () => {
            window.location.replace('/')
        })
        this.socket.on('connect', () => {
            this.socket.emit('join', {
                roomId: this.roomId,
                sender: 'user'
            });
        });
        this.socket.on('connect_error', () => {
            const error_message = `Could not connect to message server. 
            Make sure that process.env.SERVER_URL in gui/frontend/.env is
            set to the server IP address and that the backend is running.`
            alert(error_message);
            console.log(error_message);
        })
    }

    loadOptions() {
        fetch(process.env.SERVER_URL + ":" + process.env.SERVER_PORT + "/" + this.roomId + "/user/options", {method: 'GET'})
            .then(response => response.json())
            .then(options => {
                this.setState({
                    options
                });
            });
    }

    async confirmOptionChange(newState) {
        this.setState(state => newState);
        await fetch(process.env.SERVER_URL + ":" + process.env.SERVER_PORT + "/" + this.roomId + "/user/options", {
            method: 'POST',
            body: JSON.stringify(newState.options),
            headers: new Headers({'content-type': 'application/json'}),
        });
    }

    async endDialog(e) {
          confirmAlert({
            customUI: ({ onClose }) => {
            return (
              <div className="confirmAlert">
                <p>Are you sure you want to move to the next dialog?</p>
                <button onClick={onClose}> No </button>
                <button
                  onClick={async () => {
                    this.socket.emit('/end_dialog_confirm', {
                        roomId: this.roomId,
                        correct: false
                    });
                    onClose();
                  }}
                >
                  Yes
                </button>
              </div>
            );
          },
          closeOnClickOutside: false
        });
    }

    async handleOptionChange(option, newValue, resetElement) {
        let newState = JSON.parse(JSON.stringify(this.state));
        newState.options[option] = newValue;
        if (newState.options.inputLanguage !== this.state.options.inputLanguage || 
            newState.options.source.address != this.state.options.source.address) {
              confirmAlert({
                customUI: ({ onClose }) => {
                return (
                  <div className="confirmAlert">
                    <p>Changing language or starting address will end the current dialog, are you sure?</p>
                    <button onClick={() => {
                        resetElement();
                        onClose();
                    }}> No </button>
                    <button
                      onClick={async () => {
                        await this.confirmOptionChange(newState);
                        this.socket.emit('/restart_dialog', {
                            roomId: this.roomId,
                            correct: false
                        });
                        onClose();
                      }}
                    >
                      Yes
                    </button>
                  </div>
                );
              },
              closeOnClickOutside: false
            });
        } else {
            this.confirmOptionChange(newState);
        }
    }

    componentDidMount() {
        document.title = `User dialog collection (${process.env.SERVER_PORT})`;
        this.loadOptions();
        this.socket.on('/update_initial_variables', () => {
            this.loadOptions();
        })
        this.socket.on('/evaluation_progress', (data) => {
            this.setState({
                options: {
                    ...this.state.options,
                    evaluationProgress: {
                        currentIndex: data.currentIndex,
                        total: data.total,
                        destinationHint: data.destinationHint
                    }
                }
            })
        })
        this.socket.on('/user_story', (data) => {
            this.setState({
                options: {
                    ...this.state.options,
                    userStory: {
                        story: data.story,
                        destinationName: data.destinationName,
                        destinationAddr: data.destinationAddr,
                        sourceAddr: data.sourceAddr
                    }
                }
            })
        })

        this.socket.on('/finished_evaluation', (data) => {
            confirmAlert({
                customUI: ({ onClose }) => {
                    return (
                        <div className="confirmAlert">
                          <p>Finished evaluation with a score of: {Math.round(data.success_rate * 1000) / 10}%</p>
                          <p>Thank you for participating in our evaluation!</p>
                          <button onClick={onClose}>Close</button>
                        </div>
                    );
                }
            });
        });
    }

    preloadUserStory(){
        if (Object.keys(this.state.options.userStory).length == 0) {
            return <div></div>
        } else {
            return (
                <div>
                    <p>1. Please read the following descriptions about the trip:</p>
                    {
                        (this.state.options.userStory.story != []) && (

                            <ul>
                                {this.state.options.userStory.story.map(function(item) {
                                    return <li><a style="color:red">{item}</a></li>;
                                })}
                                <li>starting address: {this.state.options.userStory.sourceAddr} <b>(please don't mention this to the agent)</b></li>
                                <li>destination: {this.state.options.userStory.destinationName}, {this.state.options.userStory.destinationAddr} <b>(please don't mention this to the agent)</b></li>
                            </ul>

                        )
                    }
                    <p>2. Please read the chat history in the chat box. It could be empty if you are the first one to chat.</p>
                    <p>3. Based on the trip descriptions and the chat history, please read the following instructions to complete <b>one turn</b> of the conversation:</p>
                    <ul>
                        <li>Please send one message about <b>ONE</b> point of the descriptions that has not been mentioned.</li>
                        <li>Please <b>paraphrase your messages</b> as much as possible.</li>
                        <li>If the descriptions are vague, you can reply to the agent based on your preference. Please be creative! :)</li>
                        <li>You will NOT get any response from the agent at the moment.</li>
                        <li>After sending messages, simply close the web page and go back to MTURK page to submit the task.</li>
                    </ul>
                    <p>4. If all descriptions of the destination are covered in the chat history and you think the agent gets the right destination, please send a message to tell the agent to start driving, e.g. "Let's go!", etc.</p>
                </div>
            )
        }
    }

    render() {
        return (
            <div class={style.home}>
                <h1>User</h1>
                <p>You are interacting as a user, trying to get to {this.state.options.evaluationProgress.endHint ? (<b>{this.state.options.evaluationProgress.endHint}</b>) : "a destination"}.</p>
                { (this.state.options.evaluationProgress.total > 0) && (
                    <p>Evaluation progress: {this.state.options.evaluationProgress.currentIndex} / {this.state.options.evaluationProgress.total} </p>
                ) }

                {/* preload user story for mturk data collection */}
                {this.preloadUserStory()}

                <ConfigPanel options={this.state.options} handleOptionChange={this.handleOptionChange} endDialog={this.endDialog}/>
                <div class={style.chatWrapper}>
                    <ChatWindow roomId={this.roomId} sender='user' socket={this.socket} extraStyles={style.chatWindow} speech={this.state.options.inputType === 'speech'} displayLanguage={this.state.options.inputLanguage} queuedMessages={[]}/>
                    {this.state.options.inputType === 'text' ?
                        <ChatInput sender='user' socket={this.socket} roomId={this.roomId}/> :
                        <SpeechInput/>
                    }
                </div>
            </div>
        );
    }
}
