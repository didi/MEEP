import style from './style';
import { h, Component } from 'preact';
import { connect } from 'react-redux';

import VariableContainer from '../variable_container/index'
import Variable from '../variable/index'

export default class APIList extends Component {
    state = {
        apis: []
    };
    onNumber = null; // keyboard listener for when a number is pressed

    async getApis() {
        const response = await fetch(`${process.env.SERVER_URL}:${process.env.SERVER_PORT}/apis`, {
            insecure: true,
            rejectUnauthorized: false
        });
        const rawAPIs = await response.json();

        this.setState({apis: rawAPIs.map((api, i) => {
            return (
                <APIVariableContainer key={api.name} name={api.name} endpoint={api.endpoint} params={api.params}
                    string={api.params.map(param => param.name + ' {}').join(', ')} variables={[]} type="api" apiIndex={i}/>
            );
        })});
    }

    componentDidMount() {
        this.getApis();

        // number keys will select the corresponding API, starting from 1
        this.onNumber = (e) => {
            let index = parseInt(e.key);
            if (isNaN(index)) {
                return; // ignore non number presses
            }
            else if (index === 0) {
                index = 10
            }

            if (index <= this.state.apis.length) {
                this.props.onAPIClick(this.state.apis[index - 1]);
            }
        }
        document.addEventListener('keydown', this.onNumber);
    }

    componentWillUnmount() {
        document.removeEventListener('keydown', this.onNumber);
    }

    render(props, state) {
        return (
            <div class={"widget " + style['api-list']}>
                <h3>APIs</h3>
                <ul>
                    {state.apis.map(api =>
                        <li onclick={e => props.onAPIClick(api)}>
                            {api}
                        </li>
                    )}
                </ul>
            </div>
        );
    }
}

/* This is bad practice, you're not supposed to extend classes in React, but it hasn't been a problem so far */
class APIVariableContainer extends VariableContainer {
    render(props, state) {
        let {name, params, endpoint, variables, variableClickHandler, type, activeVariableIndex, apiIndex} = props;
        let i = 0;
        return (

          <div class={props.type + ' ' + style['variable-container']}>
            {props.keyboardMode === 'default' && props.apiIndex !== null && props.apiIndex <= 9 ? <kbd>{(props.apiIndex + 1) % 10}</kbd> : null}
            <div class={style.apiName}>{name}</div>
            <div>
                {state.blocks.map(block =>
                    block === '{}' ? <Variable isActive={activeVariableIndex !== undefined && i === activeVariableIndex} showName={false} v={variables[i++]} clickHandler={variableClickHandler || null}/> : block
                )}
            </div>
          </div>
        )
    }
}

const mapStateToProps = (state, ownProps) => {
    return {
        keyboardMode: state.mode,
    }
};
APIVariableContainer = connect(mapStateToProps)(APIVariableContainer)

