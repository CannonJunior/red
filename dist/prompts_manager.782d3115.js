class PromptsManager{constructor(){this.prompts=[];this.currentEditingPromptId=null;this.init();}
async init(){console.log('🎯 Initializing Prompts Manager...');this.setupEventListeners();this.setupChatAutocomplete();await this.loadPrompts();}
setupEventListeners(){document.getElementById('create-prompt-btn')?.addEventListener('click',()=>{this.openCreateModal();});document.getElementById('close-prompt-modal')?.addEventListener('click',()=>{this.closeModal();});document.getElementById('cancel-prompt-btn')?.addEventListener('click',()=>{this.closeModal();});document.getElementById('prompt-form')?.addEventListener('submit',async(e)=>{e.preventDefault();await this.savePrompt();});document.getElementById('refresh-prompts')?.addEventListener('click',async()=>{await this.loadPrompts();});document.getElementById('prompts-search')?.addEventListener('input',(e)=>{this.searchPrompts(e.target.value);});}
async loadPrompts(){try{const response=await fetch('/api/prompts');const data=await response.json();if(data.status==='success'){this.prompts=data.prompts||[];this.renderPrompts();this.updateStats();console.log(`✅ Loaded ${this.prompts.length} prompts`);}else{console.error('Failed to load prompts:',data.message);this.showNotification('Failed to load prompts','error');}}catch(error){console.error('Error loading prompts:',error);this.showNotification('Error loading prompts','error');}}
renderPrompts(promptsToRender=null){const prompts=promptsToRender||this.prompts;const tableBody=document.getElementById('prompts-table-body');const emptyState=document.getElementById('prompts-empty-state');if(!tableBody)return;if(prompts.length===0){tableBody.innerHTML='';emptyState?.classList.remove('hidden');return;}
emptyState?.classList.add('hidden');tableBody.innerHTML=prompts.map(prompt=>`
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${this.escapeHtml(prompt.name)}</div>
                </td>
                <td class="px-6 py-4">
                    <div class="text-sm text-gray-600 dark:text-gray-400">${this.escapeHtml(prompt.description)}</div>
                </td>
                <td class="px-6 py-4">
                    <code class="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-blue-600 dark:text-blue-400">/${this.escapeHtml(prompt.name)}</code>
                </td>
                <td class="px-6 py-4">
                    ${prompt.mcp_enabled ?
                        '<span class="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">Enabled</span>' :
                        '<span class="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">Disabled</span>'
                    }
                </td>
                <td class="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                    ${prompt.usage_count || 0}
                </td>
                <td class="px-6 py-4 text-right text-sm space-x-2">
                    <button onclick="promptsManager.editPrompt('${prompt.id}')" class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">
                        Edit
                    </button>
                    <button onclick="promptsManager.deletePrompt('${prompt.id}')" class="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300">
                        Delete
                    </button>
                </td>
            </tr>
        `).join('');}
updateStats(){document.getElementById('prompts-count').textContent=this.prompts.length;document.getElementById('prompts-mcp-count').textContent=this.prompts.filter(p=>p.mcp_enabled).length;document.getElementById('prompts-usage-count').textContent=this.prompts.reduce((sum,p)=>sum+(p.usage_count||0),0);}
openCreateModal(){this.currentEditingPromptId=null;document.getElementById('prompt-modal-title').textContent='Create Prompt';document.getElementById('prompt-form').reset();document.getElementById('prompt-id').value='';document.getElementById('prompt-mcp-enabled').checked=true;document.getElementById('prompt-modal').classList.remove('hidden');}
async editPrompt(promptId){const prompt=this.prompts.find(p=>p.id===promptId);if(!prompt)return;this.currentEditingPromptId=promptId;document.getElementById('prompt-modal-title').textContent='Edit Prompt';document.getElementById('prompt-id').value=prompt.id;document.getElementById('prompt-name').value=prompt.name;document.getElementById('prompt-description').value=prompt.description||'';document.getElementById('prompt-content').value=prompt.content;document.getElementById('prompt-mcp-enabled').checked=prompt.mcp_enabled!==false;document.getElementById('prompt-modal').classList.remove('hidden');}
closeModal(){document.getElementById('prompt-modal').classList.add('hidden');this.currentEditingPromptId=null;}
async savePrompt(){const promptId=document.getElementById('prompt-id').value;const name=document.getElementById('prompt-name').value.trim();const description=document.getElementById('prompt-description').value.trim();const content=document.getElementById('prompt-content').value.trim();const mcp_enabled=document.getElementById('prompt-mcp-enabled').checked;if(!name||!content){this.showNotification('Name and content are required','error');return;}
const promptData={name,description,content,mcp_enabled};try{let response;if(promptId){response=await fetch(`/api/prompts/${promptId}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(promptData)});}else{response=await fetch('/api/prompts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(promptData)});}
const data=await response.json();if(data.status==='success'){this.showNotification(data.message,'success');this.closeModal();await this.loadPrompts();}else{this.showNotification(data.message||'Failed to save prompt','error');}}catch(error){console.error('Error saving prompt:',error);this.showNotification('Error saving prompt','error');}}
async deletePrompt(promptId){const prompt=this.prompts.find(p=>p.id===promptId);if(!prompt)return;if(!confirm(`Delete prompt "${prompt.name}"?`))return;try{const response=await fetch(`/api/prompts/${promptId}`,{method:'DELETE'});const data=await response.json();if(data.status==='success'){this.showNotification('Prompt deleted successfully','success');await this.loadPrompts();}else{this.showNotification(data.message||'Failed to delete prompt','error');}}catch(error){console.error('Error deleting prompt:',error);this.showNotification('Error deleting prompt','error');}}
async searchPrompts(query){if(!query.trim()){this.renderPrompts();return;}
try{const response=await fetch('/api/prompts/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:query.trim()})});const data=await response.json();if(data.status==='success'){this.renderPrompts(data.prompts);}}catch(error){console.error('Error searching prompts:',error);}}
async getPromptByName(name){try{const response=await fetch('/api/prompts/use',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});const data=await response.json();if(data.status==='success'){return data.data.content;}
return null;}catch(error){console.error('Error getting prompt:',error);return null;}}
escapeHtml(text){const div=document.createElement('div');div.textContent=text;return div.innerHTML;}
setupChatAutocomplete(){const messageInput=document.getElementById('messageInput');const autocompleteDropdown=document.getElementById('prompts-autocomplete');const autocompleteList=document.getElementById('prompts-autocomplete-list');if(!messageInput||!autocompleteDropdown||!autocompleteList){console.warn('Chat autocomplete elements not found, skipping setup');return;}
let selectedIndex=-1;messageInput.addEventListener('input',(e)=>{const text=e.target.value;const cursorPos=e.target.selectionStart;const textBeforeCursor=text.substring(0,cursorPos);const lastSlashIndex=textBeforeCursor.lastIndexOf('/');if(lastSlashIndex!==-1){const searchTerm=textBeforeCursor.substring(lastSlashIndex+1);const charBeforeSlash=lastSlashIndex>0?text[lastSlashIndex-1]:' ';if(charBeforeSlash===' '||lastSlashIndex===0){this.showAutocomplete(searchTerm,autocompleteDropdown,autocompleteList,messageInput);selectedIndex=-1;return;}}
this.hideAutocomplete(autocompleteDropdown);});messageInput.addEventListener('keydown',(e)=>{if(!autocompleteDropdown.classList.contains('hidden')){const items=autocompleteList.querySelectorAll('.prompt-autocomplete-item');if(e.key==='ArrowDown'){e.preventDefault();selectedIndex=Math.min(selectedIndex+1,items.length-1);this.updateAutocompleteSelection(items,selectedIndex);}else if(e.key==='ArrowUp'){e.preventDefault();selectedIndex=Math.max(selectedIndex-1,0);this.updateAutocompleteSelection(items,selectedIndex);}else if(e.key==='Enter'&&selectedIndex>=0){e.preventDefault();items[selectedIndex]?.click();}else if(e.key==='Escape'){this.hideAutocomplete(autocompleteDropdown);selectedIndex=-1;}}});document.addEventListener('click',(e)=>{if(!messageInput.contains(e.target)&&!autocompleteDropdown.contains(e.target)){this.hideAutocomplete(autocompleteDropdown);}});}
showAutocomplete(searchTerm,dropdown,list,input){const matching=this.prompts.filter(p=>p.name.toLowerCase().includes(searchTerm.toLowerCase()));if(matching.length===0){this.hideAutocomplete(dropdown);return;}
list.innerHTML=matching.map(prompt=>`
            <div class="prompt-autocomplete-item px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
                 data-prompt-id="${prompt.id}"
                 data-prompt-name="${this.escapeHtml(prompt.name)}">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-sm font-medium text-gray-900 dark:text-white">
                            /${this.escapeHtml(prompt.name)}
                        </div>
                        <div class="text-xs text-gray-600 dark:text-gray-400">
                            ${this.escapeHtml(prompt.description)}
                        </div>
                    </div>
                    ${prompt.mcp_enabled ?
                        '<span class="text-xs text-green-600 dark:text-green-400">MCP</span>' :
                        ''
                    }
                </div>
            </div>
        `).join('');list.querySelectorAll('.prompt-autocomplete-item').forEach(item=>{item.addEventListener('click',async()=>{const promptName=item.dataset.promptName;await this.insertPrompt(promptName,input);this.hideAutocomplete(dropdown);});});dropdown.classList.remove('hidden');}
hideAutocomplete(dropdown){dropdown.classList.add('hidden');}
updateAutocompleteSelection(items,selectedIndex){items.forEach((item,index)=>{if(index===selectedIndex){item.classList.add('bg-gray-100','dark:bg-gray-700');}else{item.classList.remove('bg-gray-100','dark:bg-gray-700');}});}
async insertPrompt(promptName,input){const promptContent=await this.getPromptByName(promptName);if(!promptContent){this.showNotification(`Prompt "${promptName}" not found`,'error');return;}
const text=input.value;const cursorPos=input.selectionStart;const textBeforeCursor=text.substring(0,cursorPos);const lastSlashIndex=textBeforeCursor.lastIndexOf('/');if(lastSlashIndex!==-1){const before=text.substring(0,lastSlashIndex);const after=text.substring(cursorPos);input.value=before+promptContent+after;const newCursorPos=lastSlashIndex+promptContent.length;input.setSelectionRange(newCursorPos,newCursorPos);input.dispatchEvent(new Event('input'));}}
showNotification(message,type='info'){const toast=document.createElement('div');toast.className=`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white ${
            type === 'success' ? 'bg-green-600' :
            type === 'error' ? 'bg-red-600' :
            'bg-blue-600'
        } z-50 transition-opacity duration-300`;toast.textContent=message;document.body.appendChild(toast);setTimeout(()=>{toast.style.opacity='0';setTimeout(()=>toast.remove(),300);},3000);}}
let promptsManager=null;if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',()=>{promptsManager=new PromptsManager();window.promptsManager=promptsManager;console.log('✅ Prompts Manager attached to window');});}else{promptsManager=new PromptsManager();window.promptsManager=promptsManager;console.log('✅ Prompts Manager attached to window');}