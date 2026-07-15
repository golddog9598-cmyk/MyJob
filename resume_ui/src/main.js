import { createApp } from 'vue'
import Workspace from './Workspace.vue'
import './style.css'
import './workspace.css'
import './marketing.css'
import './tailor.css'
import { applyTheme, preferredTheme } from './theme'

applyTheme(preferredTheme())
createApp(Workspace).mount('#app')
