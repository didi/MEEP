import style from './style';
import { h, Component } from 'preact';

import VariableContainer from '../variable_container/index'
import Variable from '../variable/index'

export default class VariableList extends Component {
    componentWillReceiveProps(props) {
        if (props.variableListType === 'request_variables') {
            if (props.variables.length > 0) {
                let ending = props.variables.slice(1);
                ending.reverse()
                ending.unshift(props.variables[0])
                props.variables = ending;
            }
        }
    }

    renderVariable = (props, variable) => {
        if (Array.isArray(variable.value)) {
            return (
                <ul class={isNaN(variable.name) ? style.typeStyle : style.placeStyle}>
                    <h5>{isNaN(variable.name) ? variable.name : "Place " + variable.name}</h5>
                    {variable.value.map(v => this.renderVariable(props, v))}
                </ul>
            )
        } else {
            return (
                <li class={style[props.variableListType]}>
                    <Variable showName={props.variableListType === 'request_variables'} v={variable} clickHandler={props.selectVariable} isError={variable.name == 'error'} />
                </li>
            );
        }
    }

    render(props, state) {
        return (
            <div class={'widget ' + style['variable-widget']}>
                <h3>{props.name}</h3>
                <ul>
                {props.variables.map(response => (
                    <li>
                    <h4>{response.variable_group}</h4>
                    <h5>{response.variable_group_api_call}</h5>
                        <ul class={style.groupVariables}>
                        {
                            response.variables.map(v => this.renderVariable(props, v))
                        }
                        </ul>
                    </li>
                ))}
                </ul>
            </div>
        )
    }
}

