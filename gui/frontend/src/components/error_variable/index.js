import style from './style';
import { h, Component } from 'preact';

export default function ErrorVariable(props) {
    let {v} = props;


    const errorStyle = style.error_variable + ' ' + (v.name == 'traceback' ? style.traceback : '');
    return (
        <div class={errorStyle} onclick={() => {navigator.clipboard.writeText(v.value)}} title="Copy to clipboard">
          <span class={style.variableName}>{v.name + ": "}</span>
          {v !== undefined &&
            <span class={style.variableValue}>{v.value}</span>
          }
        </div>
    )
}
