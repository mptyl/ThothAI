# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django import forms
from django.utils.safestring import mark_safe


class PasswordInputWithToggle(forms.PasswordInput):
    """
    A password input widget with a toggle button to show/hide the password.
    Fully compatible with Django admin.
    """
    
    def render(self, name, value, attrs=None, renderer=None):
        # Generate a unique ID for this widget instance
        if attrs is None:
            attrs = {}
        
        # Ensure we have an ID for the input
        if 'id' not in attrs:
            attrs['id'] = f'id_{name}'
        
        # Set a wider size for the password field
        if 'size' not in attrs:
            attrs['size'] = '60'  # Double the default width
        
        input_id = attrs['id']
        toggle_id = f'{input_id}_toggle'
        
        # Render the standard password input
        html = super().render(name, value, attrs, renderer)
        
        # Add the toggle button and JavaScript
        toggle_html = f'''
        <div style="position: relative; display: inline-block; width: 500px; max-width: 100%;">
            {html}
            <button type="button" 
                    id="{toggle_id}"
                    style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); 
                           background: transparent; border: none; cursor: pointer; 
                           padding: 5px; font-size: 16px; z-index: 10;"
                    title="Show/Hide password"
                    onclick="(function() {{
                        var input = document.getElementById('{input_id}');
                        var button = document.getElementById('{toggle_id}');
                        if (input.type === 'password') {{
                            input.type = 'text';
                            button.innerHTML = '👁️‍🗨️';
                            button.title = 'Hide password';
                        }} else {{
                            input.type = 'password';
                            button.innerHTML = '👁️';
                            button.title = 'Show password';
                        }}
                        return false;
                    }})()"
                    onmousedown="event.preventDefault();">
                👁️
            </button>
        </div>
        <style>
            #{input_id} {{
                padding-right: 40px !important;
                width: 100% !important;
                box-sizing: border-box;
            }}
        </style>
        '''
        
        return mark_safe(toggle_html)