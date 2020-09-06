import { h, Component, cloneElement } from 'preact';
import style from './style';

import Notifications, {notify} from 'react-notify-toast';
import ChatWindow from '../../components/chat_window/index.js';
import io from 'socket.io-client';

import Builder from '../../components/builder/index'

export default class Agent extends Component {
    constructor(props) {
        super(props);
        this.roomId = props.roomId;
        this.initializeSocket();
        this.state = {
            request_variables: [],
            user_utterance_variables: [],
            agentName: "007"
        };
        this.agentNameChanged = this.agentNameChanged.bind(this);
    }

    initializeSocket = (roomId) => {
        this.socket = io(process.env.SERVER_URL + ":" + process.env.SERVER_PORT);
        this.socket.on('connect', () => {
            this.socket.emit('join', {
                roomId: this.roomId,
                sender: 'agent'
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
        document.title = `Agent dialog collection (${process.env.SERVER_PORT})`;

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

    async agentNameChanged(e) {
        const newName = e.target.value.trim();
        if (newName === this.state.agentName) return;
        this.setState(state => {
            return {
                ...state,
                agentName: newName
            }
        });
        const requestBody = JSON.stringify({agent_name: newName});
        const response = await fetch(this.requestPrefix + "/agent_name", {
            method: 'POST',
            body: requestBody,
            headers: new Headers({'content-type': 'application/json'})
        });
        const response_json = await response.json();
        if (response_json.status === 'ok') notify.show('Agent name successfully changed!');
    }

    render(props, state) {
        let queuedMessages = [];
        const chatWindow = <ChatWindow sender='agent' socket={this.socket} queuedMessages={queuedMessages} displayLanguage={'en'} roomId={this.roomId}/>
        const builder = <Builder chatWindow={chatWindow} socket={this.socket} requestPrefix={this.requestPrefix} queuedMessages={queuedMessages} roomId={this.roomId} includeAPIList={true} sender='agent' utteranceVariableName={"user"} />
        return (
            <div class="home" >
                <Notifications />
                <h1>Agent <input value={state.agentName} type="text" onBlur={this.agentNameChanged}/></h1>
                <p>You are interacting as an agent, trying to figure out where the user wants to go.</p>
                {builder}
            </div>
        );
    }
}
