import style from './style';
import { h, Component } from 'preact';

export default function ErrorVariable(props) {
    let {v, clickHandler, showName, typeHint, isActive, isError} = props;

    const variableStyle = "variable " + style.variable + ' ' + (isActive ? style.variableIsActive : '');
    return (
        <div class={variableStyle} onclick={clickHandler ? e => clickHandler(v, e) : null}>
          {showName &&
            <span class={style.variableName}>{v.name + ": "}</span>
          }
          {typeHint && v === undefined &&
            <span class={style.variableTypeHint}>{typeHint}</span>
          }
          {v !== undefined &&
            <span class={style.variableValue}>{v.value}</span>
          }
        </div>
    )
}
