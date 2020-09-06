import { h, Component, cloneElement } from 'preact';
import style from './style';

import Notifications, {notify} from 'react-notify-toast';
import ChatWindow from '../../components/chat_window/index';
import io from 'socket.io-client';

import Builder from '../../components/builder/index'

import { confirmAlert } from 'react-confirm-alert'; // Import
import 'react-confirm-alert/src/react-confirm-alert.css'; // Import css

export default class TemplateUser extends Component {
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

    initializeSocket = (roomId) => {
        this.socket = io(process.env.SERVER_URL + ":" + process.env.SERVER_PORT);
        this.socket.on('connect', () => {
            this.socket.emit('join', {
                roomId: this.roomId,
                sender: 'user'
            });
        });
        this.socket.on('connect_error', () => {
            const error_message = `Could not connect to message server. 
            Make sure that SERVER_URL in gui/frontend/.env is
            set to the server IP address and that the backend is running.`
            alert(error_message);
            console.log(error_message);
        })
        this.requestPrefix = process.env.SERVER_URL + ":" + process.env.SERVER_PORT + "/" + this.roomId;
    }

    componentDidMount() {
        document.title = `User dialog collection (${process.env.SERVER_PORT})`;

        const response = fetch(this.requestPrefix + "/agent_name", {
            method: 'GET'
        }).then(response => response.json())
        .then(json => this.setState(state => {
            return {
                ...state,
                agentName: json.agent_name
            }
        }));
        this.socket.on('/restart_dialog', (data) => {
            notify.show('User has restarted the dialog');
        });
    }

    render(props, state) {
        let queuedMessages = [];
        const chatWindow = <ChatWindow sender='user' socket={this.socket} queuedMessages={queuedMessages} displayLanguage={'en'} roomId={this.roomId}/>
        const builder = <Builder chatWindow={chatWindow} socket={this.socket} requestPrefix={this.requestPrefix} queuedMessages={queuedMessages} roomId={this.roomId} includeAPIList={false} sender='user' utteranceVariableName={"agent"}/>
        return (
            <div class="home">
                <Notifications />
                <h1>User</h1>
                <p>You are interacting as a user, trying to get to {this.state.options.evaluationProgress.endHint ? (<b>{this.state.options.evaluationProgress.endHint}</b>) : "a destination"}.</p>
                {builder}
            </div>
        );
    }
}

