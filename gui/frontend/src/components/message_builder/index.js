import style from './style';
import { h, Component, cloneElement } from 'preact';
import { confirmAlert } from 'react-confirm-alert'; // Import
import 'react-confirm-alert/src/react-confirm-alert.css'; // Import css


export default class MessageBuilder extends Component {
    constructor(props) {
        super();
        this.clearBuilder = null;
        this.onState = null;
        this.requestPrefix = props.requestPrefix;
    }

    keyListener = (e) => {
        if (this.clearBuilder && e.key == 'Escape') {
            this.clearBuilder();
        }
        else if (this.submitAndClear && (e.key == 'Enter' || e.key == ' ') && !e.repeat) {
            this.submitAndClear();
        }
        else if (this.queueAndClear && e.key == 'q') {
            this.queueAndClear();
        }
    }

    // bind key listeners
    componentDidMount() {
        document.addEventListener('keydown', this.keyListener)
    }

    // unbind key listeners
    componentWillUnmount() {
        document.removeEventListener('keydown', this.keyListener);
    }

    render(props, state) {
        let { activeContainer, activeVariables, activeVariableIndex, clearBuilder, clearVariable, sendMessage, queueMessage } = props;
        let activeBuilder;

        if (activeContainer) {
            let variableContainerBuilder = cloneElement(activeContainer, { variables: props.activeVariables, variableClickHandler: clearVariable, activeVariableIndex, apiIndex: null });
            let buttonText, submitFcn;
            const queueFcn = () => {
                let i = 0;
                let message = activeContainer.props.string.replace(/{.*?}/g, () => activeVariables[i++].value);
                queueMessage(message, activeContainer.props.string, activeVariables);
            }
            if (activeContainer.props.type === 'template') {
                submitFcn = () => {
                    let i = 0;
                    let message = activeContainer.props.string.replace(/{.*?}/g, () => activeVariables[i++].value);
                    sendMessage(message, activeContainer.props.string, activeVariables);
                }
            } else if (activeContainer.props.type === 'api') {
                submitFcn = async () => {
                    const requestURL = `${props.requestPrefix}${activeContainer.props.endpoint}`;
                    const requestBody = JSON.stringify(activeContainer.props.params.map((param, i) => {
                            return {
                                param: param.name,
                                variable_name: activeVariables[i].full_name,
                                value: activeVariables[i].value
                            };
                        }
                    ));
                    fetch(requestURL, {
                        method: 'POST',
                        body: requestBody,
                        headers: new Headers({ 'content-type': 'application/json' })
                    });
                    if (activeContainer.props.completesDialog) {
                        confirmAlert({
                            customUI: ({ onClose }) => {
                                return (
                                    <div className={style.confirmAlert}>
                                      <p>Waiting for the user to confirm the destination...</p>
                                      <div class={style.loader} />
                                    </div>
                                );
                            }
                        });
                    }
                }
            }

            this.clearBuilder = clearBuilder;
            this.queueAndClear = () => {
                if (props.activeVariables.filter(v => v.value !== null).length === activeContainer.props.params.length) {
                    queueFcn();
                    this.clearBuilder();
                }
            }

            this.submitAndClear = () => {
                if (props.activeVariables.filter(v => v.value !== null).length === activeContainer.props.params.length) {
                    submitFcn();
                    this.clearBuilder();
                }
            }

            activeBuilder = (
                <div>
                    {variableContainerBuilder}
                    <button class={style.builderButton} onclick={clearBuilder}>Clear</button>      
                    {activeContainer.props.type === 'template' ? <button class={style.builderButton} disabled={props.activeVariables.filter(v => v.value !== null).length !== activeContainer.props.params.length} onclick={this.queueAndClear}>
                        Queue
                    </button> : null}
                    <button class={style.builderButton} disabled={props.activeVariables.filter(v => v.value !== null).length !== activeContainer.props.params.length} onclick={this.submitAndClear}>
                        Send
                    </button>
                </div>
            )
        }
        else {
            activeBuilder = (
                // Dummy builder for a placeholder
                <div class={style['dummy-builder']}>
                    Select a template or API to continue
                </div>
            )

            // prevent repeated keypresses from re-sending messages
            this.submitAndClear = null;
            this.queueAndClear = null;
        }

        return (
            <div class={'widget ' + style['active-request']}>
                <h3>Active request</h3>
                {activeBuilder}
            </div>
        )
    }
}

