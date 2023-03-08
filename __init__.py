# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import urllib.request
import json
import bpy
bl_info = {
    "name": "BPY Chat GPT",
    "author": "Joshua Knauber",
    "description": "Integrates the Chat GPT API into Blender for script generation",
    "blender": (3, 0, 0),
    "version": (0, 0, 1),
    "location": "Text Editor -> Properties -> Chat GPT",
    "warning": "",
    "category": "Development"
}


ENDPOINT = "https://api.openai.com/v1/chat/completions"


class ChatGPTAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    api_key: bpy.props.StringProperty(
        name='API Key', description='API Key for the Chat GPT API', subtype='PASSWORD', default='')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'api_key')


class ChatHistoryItem(bpy.types.PropertyGroup):

    input: bpy.props.StringProperty()

    output: bpy.props.StringProperty()


class ChatGPTAddonProperties(bpy.types.PropertyGroup):

    chat_history: bpy.props.CollectionProperty(type=ChatHistoryItem)

    chat_gpt_input: bpy.props.StringProperty(
        name='Input', description='Input text for the Chat GPT API', default='', options={'TEXTEDIT_UPDATE'})


class GPT_OT_SendMessage(bpy.types.Operator):
    bl_label = 'Send Message'
    bl_idname = 'gpt.send_message'

    @classmethod
    def poll(cls, context):
        return context.scene.gpt.chat_gpt_input != ''

    def execute(self, context):
        gpt = context.scene.gpt

        try:
            output = process_message(request_answer(gpt.chat_gpt_input))

            text = bpy.context.space_data.text
            if text is None:
                text = bpy.data.texts.new('Chat GPT')
                bpy.context.space_data.text = text

            text.write(output)

            item = gpt.chat_history.add()
            item.input = gpt.chat_gpt_input
            item.output = output
            gpt.chat_gpt_input = ''

        except Exception as e:
            self.report({'ERROR'}, str(e))

        return {'FINISHED'}


class GPT_PT_MainPanel(bpy.types.Panel):
    bl_label = 'Chat GPT'
    bl_idname = 'GPT_PT_MainPanel'
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Chat GPT'

    def draw(self, context):
        layout = self.layout
        gpt = context.scene.gpt

        row = layout.row(align=True)
        row.scale_y = 1.25
        row.prop(gpt, 'chat_gpt_input', text='')
        row.operator('gpt.send_message', text='', icon='PLAY')


def process_message(message: str) -> str:
    """Process the message to make it more readable"""
    lines = message.split('\n')

    processed = []
    in_code_block = False
    for line in lines:
        line = line.rstrip()
        if line == '```python':
            in_code_block = True
        elif in_code_block:
            if line == '```':
                in_code_block = False
            else:
                processed.append(line)
        elif line:
            words = line.split(' ')
            while len(words) > 0:
                line = ''
                while len(words) > 0 and len(line) + len(words[0]) < 80:
                    line += words.pop(0) + ' '
                processed.append("# " + line.rstrip())
        else:
            processed.append('')

    return '\n'.join(processed)


def request_answer(text: str) -> str:
    """Request an answer from the Chat GPT API"""
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful coding assistant for writing python scripts in the 3D software Blender."},
            {"role": "user", "content": text}
        ],
        "temperature": 0,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bpy.context.preferences.addons[__name__].preferences.api_key}",
    }

    req = urllib.request.Request(ENDPOINT, json.dumps(data).encode(), headers)

    with urllib.request.urlopen(req) as response:
        answer = json.loads(response.read().decode())

    if 'error' in answer:
        raise Exception(answer['error']['message'])

    output = answer['choices'][0]['message']['content']
    return output


def register():
    bpy.utils.register_class(GPT_PT_MainPanel)
    bpy.utils.register_class(GPT_OT_SendMessage)

    bpy.utils.register_class(ChatHistoryItem)
    bpy.utils.register_class(ChatGPTAddonProperties)

    bpy.utils.register_class(ChatGPTAddonPreferences)

    bpy.types.Scene.gpt = bpy.props.PointerProperty(
        type=ChatGPTAddonProperties)


def unregister():
    bpy.utils.unregister_class(GPT_PT_MainPanel)
    bpy.utils.unregister_class(GPT_OT_SendMessage)

    bpy.utils.unregister_class(ChatHistoryItem)
    bpy.utils.unregister_class(ChatGPTAddonProperties)

    bpy.utils.unregister_class(ChatGPTAddonPreferences)

    del bpy.types.Scene.gpt
