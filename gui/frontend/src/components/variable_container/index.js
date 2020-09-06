import style from './style';
import { h, Component } from 'preact';

import Variable from '../variable/index'

export default class VariableContainer extends Component {
    constructor(props) {
        super();

        let {string, type} = props; // string: a raw string with {} for variables. type: either 'api' or 'template'
        let blocks = string.split(/({.*?})/);
        this.state = {...props, blocks};

        props.numVariables = blocks.filter(block => /{.*}/.test(block)); // you're not supposed to modify props, but this is derived from props
    }

    render(props, state) {
        let {variableClickHandler, variables, type, activeVariableIndex} = props;
        let i = 0;

        return (
            <div onclick={props.onclick} class={props.type + ' variable-container ' + style['variable-container']}>
                {state.blocks.map(block => {
                    const m = /{(.*)}/.exec(block);
                    return m ? <Variable
                        isActive={activeVariableIndex !== undefined && i === activeVariableIndex}
                        showName={false}
                        typeHint={m[1] || null}
                        v={variables[i++]}
                        clickHandler={variableClickHandler || null}
                    /> : block;
                })}
            </div>
        )
    }
}

