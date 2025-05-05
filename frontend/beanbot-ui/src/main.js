// main.js
import { createApp } from 'vue';
import PrimeVue from 'primevue/config';
import Nora from '@primevue/themes/nora'
import ToastService from 'primevue/toastservice';

// Import PrimeVue theme (using official theme package)
import 'primeicons/primeicons.css';                     // Icons
import 'primeflex/primeflex.css';                       // PrimeFlex for layout

// Import PrimeVue components (to be used globally)
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Select from 'primevue/select';
import DatePicker from 'primevue/datepicker';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Dialog from 'primevue/dialog';
import AutoComplete from 'primevue/autocomplete';
import InputSwitch from 'primevue/inputswitch';
import Tag from 'primevue/tag';
import Paginator from 'primevue/paginator';
import MultiSelect from 'primevue/multiselect';
import Message from 'primevue/message';
import ProgressBar from 'primevue/progressbar';
import Divider from 'primevue/divider';
import Toast from 'primevue/toast';

import App from './App.vue';

const app = createApp(App);
app.use(PrimeVue, {
    theme: {
        preset: Nora
    }
});
app.use(ToastService);

// Register PrimeVue components globally
app.component('Button', Button);
app.component('InputText', InputText);
app.component('Select', Select);
app.component('DatePicker', DatePicker);
app.component('DataTable', DataTable);
app.component('Column', Column);
app.component('Dialog', Dialog);
app.component('AutoComplete', AutoComplete);
app.component('InputSwitch', InputSwitch);
app.component('Tag', Tag);
app.component('Paginator', Paginator);
app.component('MultiSelect', MultiSelect);
app.component('Message', Message);
app.component('ProgressBar', ProgressBar);
app.component('Divider', Divider);
app.component('Toast', Toast);

app.mount('#app');
