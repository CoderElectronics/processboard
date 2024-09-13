/* alpinejs */
import Alpine from 'alpinejs';
import persist from '@alpinejs/persist'

window.persist = persist;
Alpine.plugin(persist);
window.Alpine = Alpine;
Alpine.start();

/* event bus */
window.eventBus = require('js-event-bus')();
