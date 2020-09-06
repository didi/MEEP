import { h, Component } from 'preact';
import style from './style';

export default class ChatMessage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            showBreakdown: false
        }
        this.handleClick = this.handleClick.bind(this);
    }

    handleClick(e) {
        if (["dropdown2", "dropdown4"].includes(this.props.sender)) {
            fetch(`${process.env.SERVER_URL}:${process.env.SERVER_PORT}/${this.props.roomId}/execute_alternate_action`,
                {
                    method: 'POST',
                    body: JSON.stringify(
                        {
                            id: this.props.id,
                            roomId : this.props.roomId,
                            dropdown_indices_and_lengths: this.props.dropdown_indices_and_lengths
                        }
                        ),
                    headers: new Headers({'content-type': 'application/json'})
                }
            );
        } else {
            this.setState(state => ({
                showBreakdown: !state.showBreakdown
            }));
        }
        e.stopPropagation();
    }

    // Events for correction interface
    displayEvent(e) {
        if (e["event_type"] == "api_call") {
            let params = e["params"].map(x => x["variable_name"]).join(", ")
            if (e["variables"] && e["variables"].length > 0) {
                let short_name_variables = e["variables"].flatMap(x => {
                    if ("full_name" in x) {
                        return x["full_name"]
                    } else {
                        // TODO are there any cases where 'full_name' would be nested
                        //      somewhere other than inside a 'value' list?
                        return x['value'].map(y => y["full_name"])
                    }
                }).filter(x => x!= undefined)
                    .map(x => x.split("_")[0])
                    .reduce((unique, item) =>
                        unique.includes(item) ? unique : [...unique, item], [])
                    .join(", ")
                return `API_CALL -> [${short_name_variables}]: ${e["endpoint"]}(${params})`
            } else {
                return `API_CALL: ${e["endpoint"]}(${params})`
            }
        } else if (e["event_type"] == "agent_utterance") {
            return `TMPL: ${e["template"]} [${e["params"].join(", ")}] `
        } else if (e["event_type"] == "wait_for_user") {
            return "REMOVE_ACTION"
        } else if (e["event_type"] == "user_utterance") {
            return `USER_UTTERANCE`
        } else {
            return "UNKNOWN EVENT CHECK CONSOLE F12"
        }
    }

    dropdownSender(sender) {
        if (sender == 'them') return 'dropdown1'
        if (sender == 'dropdown1') return 'dropdown2'
        if (sender == 'me') return 'dropdown3'
        if (sender == 'dropdown3') return 'dropdown4'
    }

    render(props, state) {
        return (
            (props.active_index === undefined || props.active_index != props.index) &&
            props.event_type !== "end_dialog" &&
            <li class={style.messageWrapper} onClick={this.handleClick}>
                <div class={style.message + ' ' + style[props.sender]}>
                    {props.body}
                    {props.options && props.options.length > 0 && (
                        <ul class={style[props.sender]}>
                        {props.options.map(props.showMessageOptions)}
                        </ul>
                    )}
                </div>
                <ul>
                    {
                    // Recursively more dropdowns.  Note that this isn't a fully recursive solution, the code
                    // assumes the dropdowns only go two levels deep, and that the second level of dropdowns
                    // gets its events from the hard-coded "alternate_events.events" field.
                        state.showBreakdown && props.dropdown_events && props.dropdown_events.length > 0 &&
                        props.dropdown_events.map((e, index) => {return(
                            <ChatMessage key={index}
                                         roomId={props.roomId}
                                         sender={this.dropdownSender(props.sender)}
                                         body={this.displayEvent(e)}
                                         dropdown_events={e.alternate_events ?
                                             e.alternate_events.events.map(sub_event => {return(
                                                 {...sub_event, active_index: e.alternate_events.active_index})}) : null}
                                         active_index={e.active_index}
                                         index={index}
                                         id={props.id}
                                         dropdown_indices_and_lengths={[...props.dropdown_indices_and_lengths,
                                                                       [index, props.dropdown_events.length]]}
                                         event_type={e.event_type}
                                         socket={props.socket}
                                         />
                        )})
                    }
                </ul>
            </li>
        );
    }
}
