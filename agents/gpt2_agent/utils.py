import re
from nltk.tokenize.treebank import TreebankWordDetokenizer
from collections import OrderedDict

detokenizer = TreebankWordDetokenizer()


def parse_action(text):
    '''
    Extract the action from a prediction
    '''
    text = text[:text.find('[PARAM]')] if '[PARAM]' in text else text
    return text[len('[ACTION]'):].strip()


def parse_params(text):
    '''
    Extract the parameters from a prediction
    '''
    return text.partition('[PARAM]')[2].strip().split(
        ' [PARAM] ') if '[PARAM]' in text else []


def preprocess_context(context_lines):
    '''
    Preprocess the context to split on underscores
    '''
    context_lines = [line.replace('_', ' ') for line in context_lines]
    # return new_lines
    variable_replaced_lines = []
    variable_dict = {}
    for line in context_lines:
        match = re.match('(.*) = (.*)', line)
        if match is not None:
            variable_dict[match.group(2)] = match.group(1)
        if line.startswith('PREDICT'):
            params = parse_params(line.strip())
            if 'find place' in line or 'places nearby' in line:
                params = params[1:]
            for param in params:
                line = line.replace(param, variable_dict.get(param, param))
        variable_replaced_lines.append(line)
    return variable_replaced_lines


def get_variable_dict(context):
    variable_dict = {}
    for line in context.split('\n'):
        match = re.match('(.*) = (.*)', line)
        if match is not None:
            variable_dict[match.group(1)] = match.group(2)
    return variable_dict


def postprocess_output(text, variable_dict):
    for variable in variable_dict:
        text = text.replace(variable, variable_dict[variable])
    text = text \
        .replace('find place', 'find_place') \
        .replace('places nearby', 'places_nearby') \
        .replace('distance matrix', 'distance_matrix') \
        .replace('start driving', 'start_driving') \
        .replace('wait for user', 'wait_for_user')
    return text


def get_action_beam(model, tokenizer, context, device,
                    beam_width=1):
    tokens_to_generate = 70
    max_length = 1024
    encoded_context = tokenizer.encode(context, add_special_tokens=False, return_tensors="pt")[
        :, -(max_length - tokens_to_generate):]
    encoded_context = encoded_context.to(device)
    # Explanations of how to use generate() for beam-search:
    #     * https://huggingface.co/blog/how-to-generate  TODO try top-p and top-k sampling instead of beam search
    #     * https://huggingface.co/transformers/main_classes/model.html#transformers.PreTrainedModel.generate
    # Beam search
    output_sequences = model.generate(
        input_ids=encoded_context,
        max_length=encoded_context.shape[1] + tokens_to_generate,
        pad_token_id=198,  # stop at newline
        eos_token_id=198,  # stop at newline
        num_beams=beam_width,
        num_return_sequences=beam_width,
        do_sample=False
    )
    # Top_p sampling, doesn't seem to work well, Top-k seems to be even worse.
#    output_sequences = model.generate(
#        input_ids=encoded_context,
#        max_length=encoded_context.shape[1] + tokens_to_generate,
#        eos_token_id=198, # stop at newline
#        num_return_sequences=beam_width,
#        do_sample=True,
#        top_k=0,
#        top_p=0.95
#    )
    candidates = OrderedDict()
    variable_dict = get_variable_dict(context)
    for seq in output_sequences:
        generated_sequence = seq.tolist()
        generated_sequence = generated_sequence[encoded_context.shape[1]:]
        text = tokenizer.decode(
            generated_sequence,
            clean_up_tokenization_spaces=False)
        text = text.replace('PREDICT:', '\nPREDICT:')
        text = text[:text.find('\n')]
        text = postprocess_output(text, variable_dict)
        candidates[text] = None
    return [(parse_action(c), parse_params(c)) for c in candidates.keys()]
