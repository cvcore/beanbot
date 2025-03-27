<template>
    <div id="app">
      <Toast />
      <beancount-editor-prime />
    </div>
  </template>

  <script>
  import BeancountEditorPrime from './components/BeancountEditorPrime.vue';
  import Toast from 'primevue/toast';

  export default {
    name: 'App',
    components: {
      BeancountEditorPrime,
      Toast
    }
  };
  </script>

  <style>
  #app {
    font-family: var(--font-family);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: var(--text-color);
    margin-top: 1.25rem;
  }

  /* Add any global styles here */
  </style>
