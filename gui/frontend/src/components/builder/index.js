import style from './style';
import { h, Component } from 'preact';
import { confirmAlert } from 'react-confirm-alert'; // Import
import 'react-confirm-alert/src/react-confirm-alert.css'; // Import css

import MessageBuilder from '../message_builder/index'
import TemplateList from '../template_list/index'
import APIList from '../api_list/index'
import VariableList from '../variable_list/index'

const newMessageSound = new Audio('/me-too.mp3');

export default class Builder extends Component{
    constructor(props) {
        super(props);
        this.state = {
            activeContainer: null,
            activeVariables: null,
            activeVariableIndex: null,
            request_variables: [],
            utteranceVariables: []
        };
        this.messageQueue = [];
        this.requestPrefix = props.requestPrefix;
    }

    componentDidMount() {
        this.props.socket.on('/history/' + this.props.utteranceVariableName + '_utterance_variables', (data) => {
            console.log("Got utterance variable history", data)
            this.setState(state => {
                return {
                    ...state,
                    utteranceVariables: data
                }
            });
        });
        this.props.socket.on('/history/request_variables/' + this.props.sender, (data) => {
            this.setState(state => {
                return {
                    ...state,
                    request_variables: data
                }
            });
        });
        this.props.socket.on('/' + this.props.utteranceVariableName + '_utterance_variables', (data) => {
            console.log("Got utterance variable", data)
            this.setState(state => {
                return {
                    ...state,
                    utteranceVariables: state.utteranceVariables.concat([data])
                }
            });
        });
        this.props.socket.on('/request_variables/' + this.props.sender, (data) => {
            this.setState(state => {
                return {
                    ...state,
                    request_variables: state.request_variables.concat([data])
                }
            })
        })
        this.props.socket.on('/end_dialog_confirm', (data) => {
            const message = data.correct ? 'The user has confirmed that the dialog was successfully completed.' : 'The dialog was not successfully completed.';
            newMessageSound.play();
            confirmAlert({
                customUI: ({ onClose }) => {
                    return (
                        <div className="confirmAlert">
                          <p>{message}</p>
                          <p>Logs have been saved to {data.filename}</p>
                          <button onClick={onClose}>Close</button>
                        </div>
                    );
                }
            });
        })

        const handleKeyDown = (e) => {
            if (e.key === 'Tab' && this.state.activeVariables !== null) {
                this.setState(state => {
                    return {
                        ...this.state,
                        activeVariableIndex: (this.state.activeVariableIndex + 1) % this.state.activeVariables.length
                    }
                });
                e.preventDefault();
                e.stopPropagation();
            }
            else if (e.key == '~' || e.key == '`') {
                // populate fields with the latitude of source_variable
                this.selectRequestVariable(this.state.request_variables[0].variables[1]);
                e.stopPropagation();
            }
        }
        document.addEventListener('keydown', handleKeyDown);
    }

    selectContainer = (container) => {
        this.setState(state => {
            return {
                ...this.state,
                activeContainer: container,
                activeVariables: Array(container.props.params.length).fill({value: null}),
                activeVariableIndex: 0
            }
        });
    }

    // clears templates and API
    clearBuilder = () => {
        this.setState(state => {
            return {
                ...this.state,
                activeContainer: null,
                activeVariables: [],
                activeVariableIndex: -1
            }
        });
    }

    getNextActiveVariableIndex(activeVariables, index) {
        const originalVariableIndex = index;
        index = (index + 1) % activeVariables.length;
        while (index != originalVariableIndex && activeVariables[index].value !== null) {
            index = (index + 1) % activeVariables.length;
        }
        return index;
    }

    selectRequestVariable = (variable) => {
        if (this.state.activeContainer) {
            let activeVariables = this.state.activeVariables.slice();
            let variableCopy = JSON.parse(JSON.stringify(variable));

            let nextVariableIndex = this.state.activeVariableIndex
            if (activeVariables[nextVariableIndex].full_name !== undefined && activeVariables[nextVariableIndex].full_name.startsWith("u")) {
                nextVariableIndex = this.getNextActiveVariableIndex(activeVariables, nextVariableIndex);
            }
            activeVariables[nextVariableIndex] = variableCopy;
            const originalVariableIndex = nextVariableIndex;
            nextVariableIndex = this.getNextActiveVariableIndex(activeVariables, nextVariableIndex);

            this.setState(state => {
                return {
                    ...state,
                    activeVariables,
                    activeVariableIndex: nextVariableIndex
                }
            });

            // If we clicked latitude, find the corresponding longitude variable (it's what we always will want)
            if (variable.name.includes && variable.name.includes('latitude')
                && nextVariableIndex !== originalVariableIndex
                && this.state.activeContainer.props.type !== 'template'
                && this.state.activeContainer.props.params[originalVariableIndex].name.includes("latitude")) {
                for (let variableGroup in this.state.request_variables) {
                    for (let otherVariableIndex in this.state.request_variables[variableGroup].variables) {
                        let otherVariable = this.state.request_variables[variableGroup].variables[otherVariableIndex];
                        if (Array.isArray(otherVariable.value)) {
                            otherVariable.value.forEach(childVariable => this.findLongitude(childVariable, activeVariables, variable, originalVariableIndex, nextVariableIndex));
                        } else {
                            this.findLongitude(otherVariable, activeVariables, variable, originalVariableIndex, nextVariableIndex);
                        }
                    }
                }
            }
        }
    }

    findLongitude = (variable, activeVariables, originalVariable, originalVariableIndex, nextVariableIndex) => {
        if (originalVariable.full_name.replace("latitude", "longitude") !== variable.full_name) return;
        // Found the corresponding longitude variable for the selected latitude variable
        for (let paramIndex in this.state.activeContainer.props.params) {
            if (this.state.activeContainer.props.params[paramIndex].name !==
                this.state.activeContainer.props.params[originalVariableIndex].name.replace("latitude", "longitude")) continue;
            activeVariables[paramIndex] = variable;
            nextVariableIndex = this.getNextActiveVariableIndex(activeVariables, nextVariableIndex);
            this.setState(state => {
                return {
                    ...state,
                    activeVariables,
                    activeVariableIndex: nextVariableIndex
                }
            });
            return;
        }
    }

    selectUserVariable = (variable) => {
        if (this.state.activeContainer) {
            let activeVariables = this.state.activeVariables.slice(); // copy because state is immutable
            let variableCopy = JSON.parse(JSON.stringify(variable));

            let nextVariableIndex = this.state.activeVariableIndex
            if (nextVariableIndex < activeVariables.length) {

                // Override normal variables
                if (activeVariables[nextVariableIndex].value === null || (activeVariables[nextVariableIndex].full_name !== undefined && !activeVariables[nextVariableIndex].full_name.startsWith("u"))) {
                    activeVariables[nextVariableIndex] = variableCopy;
                } else { // Append to user utterances
                    activeVariables[nextVariableIndex].name += ' + " " + ' + variableCopy.name;
                    activeVariables[nextVariableIndex].full_name += ' + " " + ' + variableCopy.full_name;
                    activeVariables[nextVariableIndex].value += ' ' + variableCopy.value;
                }
            }

            this.setState(state => {
                return {
                    ...state,
                    activeVariables,
                    activeVariableIndex: nextVariableIndex
                }
            });
        }
    }

    clearVariable = (variable, e) => {
        const index = Array.prototype.indexOf.call(Array.from(e.currentTarget.parentNode.childNodes).filter(v => v instanceof HTMLElement), e.currentTarget);
        let activeVariables = this.state.activeVariables.slice(); // copy because state is immutable
        activeVariables[index] = {value: null};
        this.setState(state => {
            return {
                ...state,
                activeVariables,
                activeVariableIndex: index
            }
        });
    }

    queueMessage = (message, template, activeVariables) => {
        this.props.queuedMessages.push({ roomId: this.props.roomId, sender: this.props.sender, body: message, template, variables: activeVariables.map(v => v.full_name) });
    }

    sendMessage = (message, template, activeVariables) => {
        this.props.queuedMessages.forEach(queuedMessage => {
            this.props.socket.emit('/message', queuedMessage);
        });
        this.props.queuedMessages.length = 0;
        this.props.socket.emit('/message', {
            roomId: this.props.roomId,
            sender: this.props.sender,
            body: message,
            template,
            variables: activeVariables.map(v => v.full_name)
        });
    }

    render(props, state) {
        return (
            <div class={style['builder-ui']}>
                <div class={style.col}>
                    {props.chatWindow}
                    <MessageBuilder activeContainer={state.activeContainer} activeVariables={state.activeVariables} activeVariableIndex={state.activeVariableIndex} clearBuilder={this.clearBuilder} clearVariable={this.clearVariable} sendMessage={this.sendMessage} queueMessage={this.queueMessage} requestPrefix={props.requestPrefix} />
                </div>
                <div class={style.col}>
                    <TemplateList onTemplateClick={this.selectContainer} sender={props.sender} />
                    { props.includeAPIList && <APIList onAPIClick={this.selectContainer}/> }
                </div>
                <div class={style.col}>
                    <VariableList name="Request variables" updateSource={this.updateSource} variableListType="request_variables" selectVariable={this.selectRequestVariable} variables={state.request_variables}/>
                </div>
                <div class={style.col}>
                    <VariableList name={props.utteranceVariableName.charAt(0).toUpperCase() + props.utteranceVariableName.slice(1) + " utterance variables"} variableListType="utterance_variables" selectVariable={this.selectUserVariable} variables={state.utteranceVariables}/>
                </div>
            </div>
        )
    }
}
