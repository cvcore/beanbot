<template>
  <div class="beancount-editor">
    <h1>Beancount Entries Editor</h1>

    <!-- Filter section -->
    <div class="filter-section">
      <div class="grid">
        <div class="col-12 md:col-4">
          <div class="p-inputgroup w-full">
            <InputText
              v-model="filters.narration"
              placeholder="Filter by Narration"
              class="w-full"
              @keyup.enter="loadTransactions"
            />
            <!-- <Button icon="pi pi-times" @click="clearFilter('narration')" /> -->
          </div>
        </div>
        <div class="col-12 md:col-4">
          <div class="p-inputgroup w-full">
            <InputText
              v-model="filters.account"
              placeholder="Filter by Account"
              class="w-full"
              @keyup.enter="loadTransactions"
            />
            <!-- <Button icon="pi pi-times" @click="clearFilter('account')" /> -->
          </div>
        </div>
        <div class="col-12 md:col-4">
          <Select
            v-model="filters.tag"
            :options="availableTags"
            placeholder="Filter by Tag"
            class="w-full"
            @change="loadTransactions"
            :showClear="true"
          />
        </div>
      </div>

      <div class="grid mt-2">
        <div class="col-12 md:col-4">
          <DatePicker
            v-model="filters.fromDate"
            dateFormat="yy-mm-dd"
            placeholder="From Date"
            class="w-full"
            @date-select="loadTransactions"
            :showClear="true"
          />
        </div>
        <div class="col-12 md:col-4">
          <DatePicker
            v-model="filters.toDate"
            dateFormat="yy-mm-dd"
            placeholder="To Date"
            class="w-full"
            @date-select="loadTransactions"
            :showClear="true"
          />
        </div>
        <div class="col-12 md:col-4">
          <Select
            v-model="filters.currency"
            :options="availableCurrencies"
            placeholder="Filter by Currency"
            class="w-full"
            @change="loadTransactions"
            :showClear="true"
          />
        </div>
      </div>

      <div class="grid mt-2">
        <div class="col-12">
          <Button label="Search" icon="pi pi-search" @click="loadTransactions" class="mr-2" />
          <Button label="Reset Filters" icon="pi pi-refresh" @click="resetFilters" class="p-button-secondary" />
        </div>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="loading" class="loading-container">
      <ProgressBar mode="indeterminate" style="height: 6px" />
    </div>

    <!-- Batch edit actions (visible when transactions are selected) -->
    <div v-if="!loading && selectedRows.length > 0" class="batch-actions p-3 mb-3" style="border: 1px solid var(--blue-200); background-color: var(--blue-50); border-radius: 4px;">
      <div class="flex align-items-center justify-content-between">
        <span class="font-bold">{{ selectedRows.length }} transactions selected</span>
        <div class="flex gap-2">
          <Button label="Clear Selection" class="p-button-sm p-button-text" @click="clearSelection" />
          <Button label="Predict" class="p-button-sm p-button-info" @click="predictCounterAccounts" :loading="predicting" :disabled="hasPredictions" />
          <Button v-if="hasPredictions" label="Revert Predictions" class="p-button-sm p-button-warning" @click="revertAllPredictions" />
          <Button label="Batch Edit" class="p-button-sm p-button-primary" @click="showBatchEditDialog" />
        </div>
      </div>
    </div>

    <!-- Table section -->
    <div v-if="!loading">
      <DataTable
        :value="transactions"
        v-model:selection="selectedRows"
        :rowClass="rowClassNameHandler"
        class="w-full"
        stripedRows
        dataKey="meta.beanbot_uuid"
        rowHover
        tableStyle="min-width:50rem"
        @rowSelect="onRowSelect"
        @rowUnselect="onRowUnselect"
        @rowClick="handleRowClick"
        ref="transactionTable"
        :sortMode="'single'"
        removableSort
        @sort="onSort"
        :metaKeySelection="false"
        :selectionMode="'multiple'"
        rangeMode
      >
        <!-- Selection column -->
        <Column selectionMode="multiple" headerStyle="width: 3rem" />

        <Column field="flag" header="Flag" :sortable="true">
          <template #body="slotProps">
            <Select
              v-model="slotProps.data.flag"
              :options="['*', '!']"
              optionLabel=""
              class="w-12"
            />
          </template>
        </Column>

        <Column field="date" header="Date" :sortable="true">
          <template #body="slotProps">
            <DatePicker
              v-model="slotProps.data.date"
              dateFormat="yy-mm-dd"
              placeholder="Select date"
              class="w-full"
            />
          </template>
        </Column>

        <Column field="payee" header="Payee" :sortable="true">
          <template #body="slotProps">
            <InputText
              v-model="slotProps.data.payee"
              placeholder="Enter payee"
              class="w-full"
            />
          </template>
        </Column>

        <Column field="narration" header="Narration" :sortable="true">
          <template #body="slotProps">
            <InputText
              v-model="slotProps.data.narration"
              placeholder="Enter narration"
              class="w-full"
            />
          </template>
        </Column>

        <Column field="_bookedAccount" header="Booked Account" :sortable="true">
          <template #body="slotProps">
            <AutoComplete
              v-model="slotProps.data._bookedAccount"
              :suggestions="filteredAccounts"
              @complete="searchAccounts($event, slotProps.data)"
              placeholder="Enter account"
              @change="updateBookedAccount(slotProps.data)"
              @item-select="updateBookedAccount(slotProps.data)"
              class="w-full"
            />
          </template>
        </Column>

        <Column field="_bookedAmount" header="Booked Amount" :sortable="true">
          <template #body="slotProps">
            <span>{{ getBookedAmount(slotProps.data) }}</span>
          </template>
        </Column>

        <Column field="_counterAccount" header="Counter Account(s)" :sortable="true">
          <template #body="slotProps">
            <div class="flex align-items-center gap-2 w-full">
              <span v-if="slotProps.data.predicted" class="p-tag p-tag-info" style="font-size: 0.7rem;">Predicted</span>
              <AutoComplete
                v-model="slotProps.data._counterAccount"
                :suggestions="filteredAccounts"
                @complete="searchAccounts($event, slotProps.data)"
                placeholder="Enter account"
                @change="updateCounterAccount(slotProps.data)"
                @item-select="updateCounterAccount(slotProps.data)"
                class="w-full"
                :class="{
                  'disabled-input': getCounterAccounts(slotProps.data) === 'MULTIPLE',
                  'predicted-input': slotProps.data.predicted
                }"
                :title="getCounterAccounts(slotProps.data) === 'MULTIPLE' ?
                  'Multiple counter accounts. Editing will replace them all with a single account.' : ''"
              />
            </div>
          </template>
        </Column>

        <Column field="tags" header="Tags" :sortable="true">
          <template #body="slotProps">
            <div class="tag-container flex flex-wrap gap-2 align-items-center">
              <div
                v-for="tag in slotProps.data.tags"
                :key="tag"
                class="p-1 pl-2 pr-2 rounded-md flex align-items-center gap-1 custom-tag"
              >
                <span>{{ tag }}</span>
                <Button
                  icon="pi pi-times"
                  class="p-button-rounded p-button-text p-button-sm"
                  style="width: 1.5rem; height: 1.5rem;"
                  @click.stop="removeTag(slotProps.data, tag)"
                />
              </div>
              <Button
                icon="pi pi-plus"
                class="p-button-rounded p-button-text p-button-sm"
                @click="showTagInput(slotProps.data)"
              />
            </div>
          </template>
        </Column>

        <Column header="Actions" :exportable="false">
          <template #body="slotProps">
            <Button
              label="Edit Postings"
              class="p-button-sm"
              @click.stop="editPostings(slotProps.data)"
            />
            <Button
              v-if="slotProps.data.predicted"
              icon="pi pi-undo"
              class="p-button-warning p-button-rounded p-button-sm ml-2"
              @click.stop="revertPrediction(slotProps.data)"
              title="Revert Prediction"
            />
            <Button
              icon="pi pi-check"
              class="p-button-success p-button-rounded p-button-sm ml-2"
              @click.stop="saveTransaction(slotProps.data)"
              :loading="slotProps.data.saving"
            />
          </template>
        </Column>
      </DataTable>

      <!-- Pagination -->
      <div class="pagination-container mt-3 flex justify-content-center">
        <Paginator
          v-model:rows="pageSize"
          :totalRecords="totalItems"
          v-model:first="first"
          :rowsPerPageOptions="[10, 20, 50, 100]"
          @page="onPageChange"
        />
      </div>

      <!-- Save all changes button -->
      <div class="action-buttons mt-3 flex justify-content-end gap-2">
        <Button
          label="Reload From Disk"
          icon="pi pi-refresh"
          @click="reloadFromDisk"
          :loading="reloading"
          class="p-button-secondary"
        />
        <Button
          label="Train Model"
          icon="pi pi-sync"
          @click="trainModel"
          :loading="training"
          class="p-button-info"
        />
        <Button
          label="Save All Changes"
          icon="pi pi-upload"
          @click="saveAllChanges"
          :loading="savingAll"
          class="p-button-success"
        />
      </div>
    </div>

    <!-- Tag Input Dialog -->
    <Dialog
      v-model:visible="tagDialogVisible"
      header="Add Tag"
      :style="{width: '400px'}"
      :modal="true"
    >
      <div class="p-fluid">
        <div class="field">
          <label for="tag-input">Tag Name</label>
          <InputText
            id="tag-input"
            v-model="newTagValue"
            placeholder="Enter tag name"
            @keydown.enter="confirmAddTag"
            autofocus
          />
          <small v-if="currentTaggedTransaction" class="block mt-1 text-color-secondary">
            Adding tag to transaction: {{ currentTaggedTransaction.narration }}
          </small>
        </div>
      </div>
      <template #footer>
        <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="tagDialogVisible = false" />
        <Button label="Add Tag" icon="pi pi-check" @click="confirmAddTag" :disabled="!newTagValue.trim()" />
      </template>
    </Dialog>

    <!-- Postings Dialog -->
    <Dialog
      v-model:visible="postingsDialogVisible"
      header="Edit Postings"
      :style="{width: '80%'}"
      :modal="true"
    >
      <div v-if="currentTransaction">
        <div v-for="(posting, index) in currentTransaction.postings" :key="index" class="posting-editor">
          <Divider v-if="index > 0" />
          <div class="grid">
            <div class="col-12 md:col-6">
              <div class="p-field">
                <label>Account</label>
                <AutoComplete
                  v-model="posting.account"
                  :suggestions="filteredAccounts"
                  @complete="searchAccounts($event)"
                  placeholder="Enter account"
                  class="w-full"
                />
              </div>
            </div>
            <div class="col-12 md:col-2">
              <div class="p-field">
                <label>Amount</label>
                <InputText v-model="posting.units.number" placeholder="Amount" class="w-full" />
              </div>
            </div>
            <div class="col-12 md:col-2">
              <div class="p-field">
                <label>Currency</label>
                <Select
                  v-model="posting.units.currency"
                  :options="availableCurrencies"
                  placeholder="Currency"
                  class="w-full"
                />
              </div>
            </div>
            <div class="col-12 md:col-2">
              <div class="p-field">
                <label>Missing</label>
                <InputSwitch v-model="posting.units.is_missing" />
              </div>
            </div>
          </div>

          <div class="flex justify-content-end mt-2">
            <Button
              v-if="currentTransaction.postings.length > 2"
              label="Remove Posting"
              icon="pi pi-trash"
              class="p-button-danger p-button-sm"
              @click="removePosting(index)"
            />
          </div>
        </div>

        <div class="flex justify-content-end mt-3">
          <Button label="Add Posting" icon="pi pi-plus" @click="addPosting" />
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="postingsDialogVisible = false" />
        <Button label="Save Postings" icon="pi pi-check" @click="savePostings" />
      </template>
    </Dialog>

    <!-- Batch Edit Dialog -->
    <Dialog
      v-model:visible="batchEditDialogVisible"
      header="Batch Edit Transactions"
      :style="{width: '600px'}"
      :modal="true"
      :breakpoints="{'960px': '75vw', '640px': '90vw'}"
    >
      <div class="p-fluid">
        <p class="font-bold mb-3">Editing {{ selectedRows.length }} transactions</p>

        <div class="field mb-3">
          <label for="batch-flag">Flag</label>
          <Select
            id="batch-flag"
            v-model="batchEdit.flag"
            :options="['*', '!']"
            placeholder="Select flag"
            :showClear="true"
            class="w-full"
          />
        </div>

        <div class="field mb-3">
          <label for="batch-booked-account">Booked Account</label>
          <AutoComplete
            id="batch-booked-account"
            v-model="batchEdit.bookedAccount"
            :suggestions="filteredAccounts"
            @complete="searchAccounts($event)"
            placeholder="Change booked account (first posting)"
            class="w-full"
            :showClear="true"
          />
        </div>

        <div class="field mb-3">
          <label for="batch-counter-account">Counter Account</label>
          <AutoComplete
            id="batch-counter-account"
            v-model="batchEdit.counterAccount"
            :suggestions="filteredAccounts"
            @complete="searchAccounts($event)"
            placeholder="Change counter account"
            class="w-full"
            :showClear="true"
          />
          <small class="text-color-secondary block mt-1">
            Note: If a transaction has multiple counter accounts, they will all be replaced with this account.
          </small>
        </div>

        <div class="field mb-3">
          <label for="batch-add-tags">Add tags</label>
          <MultiSelect
            id="batch-add-tags"
            v-model="batchEdit.addTags"
            :options="availableTags"
            placeholder="Select tags to add"
            class="w-full"
            display="chip"
          />
        </div>

        <div class="field mb-3">
          <label for="batch-remove-tags">Remove tags</label>
          <MultiSelect
            id="batch-remove-tags"
            v-model="batchEdit.removeTags"
            :options="allTagsInSelected"
            placeholder="Select tags to remove"
            class="w-full"
            display="chip"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="batchEditDialogVisible = false" />
        <Button label="Apply Changes" icon="pi pi-check" @click="applyBatchEdit" autofocus />
      </template>
    </Dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, nextTick } from 'vue';
import { useToast } from 'primevue/usetoast';
import axios from 'axios';
import _ from 'lodash';

// Import missing PrimeVue components
import ProgressBar from 'primevue/progressbar';
import Divider from 'primevue/divider';
import Toast from 'primevue/toast';
import Tag from 'primevue/tag';
import DatePicker from 'primevue/datepicker';
import Select from 'primevue/select';

// API base URL - change this to match your FastAPI server
const API_BASE_URL = 'http://localhost:8000/api';

export default {
  name: 'BeancountEditorPrime',
  components: {
    ProgressBar,
    Divider,
    Toast,
    Tag,
    DatePicker,
    Select
  },
  setup() {
    const toast = useToast();

    // State
    const transactions = ref([]);
    const originalTransactions = ref([]);
    const availableAccounts = ref([]);
    const availableTags = ref([]);
    const availableCurrencies = ref([]);
    const loading = ref(false);
    const savingAll = ref(false);
    const reloading = ref(false);
    const training = ref(false);
    const predicting = ref(false);
    const tagDialogVisible = ref(false);
    const postingsDialogVisible = ref(false);
    const batchEditDialogVisible = ref(false);
    const newTagValue = ref('');
    const currentTransaction = ref(null);
    const currentTaggedTransaction = ref(null);
    const totalItems = ref(0);
    const pageSize = ref(20);
    const first = ref(0);
    const transactionTable = ref(null);
    const selectedRows = ref([]);
    const filteredAccounts = ref([]);
    const predictedTransactions = ref(new Map()); // Map to store original state of predicted transactions

    // Batch edit state
    const batchEdit = reactive({
      flag: '',
      addTags: [],
      removeTags: [],
      bookedAccount: '',
      counterAccount: ''
    });

    // Filters
    const filters = reactive({
      narration: '',
      account: '',
      fromDate: null,
      toDate: null,
      tag: null,
      currency: null
    });

    // Computed properties
    const selectedTransactions = computed(() => {
      console.log('Computing selectedTransactions, count:', selectedRows.value.length);
      return selectedRows.value || [];
    });

    const allTagsInSelected = computed(() => {
      const allTags = new Set();
      selectedTransactions.value.forEach(tx => {
        tx.tags.forEach(tag => allTags.add(tag));
      });
      return Array.from(allTags);
    });

    const hasPredictions = computed(() => {
      return predictedTransactions.value.size > 0;
    });

    // Check if transaction has been modified
    const isTransactionChanged = (transaction) => {
      const original = originalTransactions.value.find(
        t => t.meta.beanbot_uuid === transaction.meta.beanbot_uuid
      );

      if (!original) return false;

      // Deep compare transaction with original, excluding 'saving' property
      const tx1 = _.cloneDeep(transaction);
      const tx2 = _.cloneDeep(original);

      // Remove properties we don't want to compare
      delete tx1.saving;
      delete tx2.saving;

      return !_.isEqual(tx1, tx2);
    };

    // Load reference data
    const loadReferenceData = async () => {
      try {
        const [accountsResponse, tagsResponse, currenciesResponse] = await Promise.all([
          axios.get(`${API_BASE_URL}/accounts`),
          axios.get(`${API_BASE_URL}/tags`),
          axios.get(`${API_BASE_URL}/currencies`)
        ]);

        availableAccounts.value = accountsResponse.data;
        availableTags.value = tagsResponse.data;
        availableCurrencies.value = currenciesResponse.data;
      } catch (error) {
        console.error('Error loading reference data:', error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load reference data', life: 3000 });
      }
    };

    // Load transactions with current filters and pagination
    const loadTransactions = async () => {
      loading.value = true;

      try {
        // Build query parameters
        const params = {
          page: Math.floor(first.value / pageSize.value) + 1,
          page_size: pageSize.value
        };

        if (filters.narration) params.narration = filters.narration;
        if (filters.account) params.account = filters.account;
        if (filters.fromDate) {
          // Convert Date object to string format (YYYY-MM-DD)
          const fromDate = filters.fromDate instanceof Date
            ? filters.fromDate.toISOString().split('T')[0]
            : filters.fromDate;
          params.from_date = fromDate;
        }
        if (filters.toDate) {
          // Convert Date object to string format (YYYY-MM-DD)
          const toDate = filters.toDate instanceof Date
            ? filters.toDate.toISOString().split('T')[0]
            : filters.toDate;
          params.to_date = toDate;
        }
        if (filters.tag) params.tag = filters.tag;
        if (filters.currency) params.currency = filters.currency;

        const response = await axios.get(`${API_BASE_URL}/transactions`, { params });

        // Update state
        transactions.value = response.data.data.items;

        // Process each transaction to add UI-specific properties
        transactions.value.forEach(tx => {
          // Add saving flag
          tx.saving = false;

          // Initialize editable account fields
          tx._bookedAccount = tx.postings.length > 0 ? tx.postings[0].account : '';

          // Initialize counter account field
          if (tx.postings.length > 1) {
            const counterAccounts = tx.postings.slice(1).map(p => p.account);
            tx._counterAccount = counterAccounts.length === 1 ? counterAccounts[0] : 'MULTIPLE';
          } else {
            tx._counterAccount = '';
          }
        });

        // Store original state for change detection
        originalTransactions.value = _.cloneDeep(transactions.value);

        totalItems.value = response.data.data.total;

        // Clear any previous selection
        selectedRows.value = [];

      } catch (error) {
        console.error('Error loading transactions:', error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load transactions', life: 3000 });
      } finally {
        loading.value = false;
      }
    };

    // Reset all filters
    const resetFilters = () => {
      Object.keys(filters).forEach(key => {
        filters[key] = null;
      });
      loadTransactions();
    };

    // Clear a specific filter
    const clearFilter = (filterName) => {
      filters[filterName] = null;
      loadTransactions();
    };

    // Pagination event handler
    const onPageChange = (event) => {
      first.value = event.first;
      pageSize.value = event.rows;
      loadTransactions();
    };

    // Row selection handlers
    const onRowSelect = (event) => {
      console.log('Row selected:', event.data.meta.beanbot_uuid);
    };

    const onRowUnselect = (event) => {
      console.log('Row unselected:', event.data.meta.beanbot_uuid);
    };

    // Handle row click for multiple selection
    const handleRowClick = (event) => {
      console.log('Row clicked');
      // PrimeVue now handles shift-click and ctrl-click selection with rangeMode
    };

    // Clear all selections
    const clearSelection = () => {
      console.log('Clearing selection');
      selectedRows.value = [];
    };

    // Account searching for AutoComplete
    const searchAccounts = (event, data) => {
      const query = event.query.toLowerCase();
      filteredAccounts.value = availableAccounts.value.filter(
        account => account.toLowerCase().includes(query)
      );
    };

    // Tag operations
    const showTagInput = (transaction) => {
      currentTaggedTransaction.value = transaction;
      newTagValue.value = '';
      tagDialogVisible.value = true;
    };

    const confirmAddTag = () => {
      const tag = newTagValue.value.trim();
      if (tag && currentTaggedTransaction.value) {
        // Create a new array to trigger reactivity
        currentTaggedTransaction.value.tags = [
          ...currentTaggedTransaction.value.tags,
          tag
        ];
      }
      tagDialogVisible.value = false;
    };

    const removeTag = (transaction, tag) => {
      transaction.tags = transaction.tags.filter(t => t !== tag);
    };

    // Posting operations
    const editPostings = (transaction) => {
      currentTransaction.value = JSON.parse(JSON.stringify(transaction)); // Deep clone
      postingsDialogVisible.value = true;
    };

    const addPosting = () => {
      if (!currentTransaction.value) return;

      // Create a default empty posting
      const newPosting = {
        account: '',
        units: {
          number: null,
          currency: availableCurrencies.value[0] || 'USD'
        },
        cost: null,
        price: null,
        flag: null,
        meta: {}
      };

      currentTransaction.value.postings.push(newPosting);
    };

    const removePosting = (index) => {
      if (!currentTransaction.value || currentTransaction.value.postings.length <= 2) return;
      currentTransaction.value.postings.splice(index, 1);
    };

    const savePostings = () => {
      if (!currentTransaction.value) return;

      // Find the original transaction and update it
      const index = transactions.value.findIndex(t =>
        t.meta.beanbot_uuid === currentTransaction.value.meta.beanbot_uuid
      );

      if (index >= 0) {
        // Only update the postings
        transactions.value[index].postings = currentTransaction.value.postings;

        // Update editable account fields
        transactions.value[index]._bookedAccount = transactions.value[index].postings.length > 0
          ? transactions.value[index].postings[0].account
          : '';

        // Update counter account field
        if (transactions.value[index].postings.length > 1) {
          const counterAccounts = transactions.value[index].postings.slice(1).map(p => p.account);
          transactions.value[index]._counterAccount = counterAccounts.length === 1
            ? counterAccounts[0]
            : 'MULTIPLE';
        } else {
          transactions.value[index]._counterAccount = '';
        }
      }

      postingsDialogVisible.value = false;
    };

    // Batch editing
    const showBatchEditDialog = () => {
      console.log('Showing batch edit dialog, selected rows:', selectedRows.value.length);
      // Reset batch edit form
      batchEdit.flag = '';
      batchEdit.addTags = [];
      batchEdit.removeTags = [];
      batchEdit.bookedAccount = '';
      batchEdit.counterAccount = '';

      batchEditDialogVisible.value = true;
    };

    const applyBatchEdit = () => {
      const selected = selectedRows.value;
      if (!selected.length) {
        toast.add({ severity: 'warn', summary: 'Warning', detail: 'No transactions selected for batch edit', life: 3000 });
        return;
      }

      console.log('Applying batch edits to', selected.length, 'transactions');

      selected.forEach(transaction => {
        // Update flag if specified
        if (batchEdit.flag) {
          transaction.flag = batchEdit.flag;
        }

        // Update booked account (first posting)
        if (batchEdit.bookedAccount && transaction.postings.length > 0) {
          transaction.postings[0].account = batchEdit.bookedAccount;
          transaction._bookedAccount = batchEdit.bookedAccount;
        }

        // Update counter account (remaining postings)
        if (batchEdit.counterAccount && transaction.postings.length > 1) {
          // If there are multiple counter accounts
          if (transaction.postings.length > 2) {
            // Keep only the first posting (booked account) and the first counter account
            transaction.postings = transaction.postings.slice(0, 2);
          }

          // Update the counter account (second posting)
          transaction.postings[1].account = batchEdit.counterAccount;
          transaction._counterAccount = batchEdit.counterAccount;

          // Set missing values for the amount
          if (!transaction.postings[1].units) {
            transaction.postings[1].units = "__MISSING__";
          }
        }

        // Add tags
        if (batchEdit.addTags && batchEdit.addTags.length) {
          // Ensure tags array exists
          if (!Array.isArray(transaction.tags)) {
            transaction.tags = [];
          }

          const currentTags = new Set(transaction.tags);
          batchEdit.addTags.forEach(tag => currentTags.add(tag));
          transaction.tags = Array.from(currentTags);
        }

        // Remove tags
        if (batchEdit.removeTags && batchEdit.removeTags.length && Array.isArray(transaction.tags)) {
          transaction.tags = transaction.tags.filter(tag =>
            !batchEdit.removeTags.includes(tag)
          );
        }
      });

      batchEditDialogVisible.value = false;
      toast.add({ severity: 'success', summary: 'Success', detail: `Changes applied to ${selected.length} transactions`, life: 3000 });
    };

    // Save a single transaction
    const saveTransaction = async (transaction) => {
      transaction.saving = true;

      try {
        const uuid = transaction.meta.beanbot_uuid;
        await axios.put(`${API_BASE_URL}/transactions/${uuid}`, transaction);

        // Update original state after successful save
        const index = originalTransactions.value.findIndex(t => t.meta.beanbot_uuid === uuid);
        if (index >= 0) {
          originalTransactions.value[index] = _.cloneDeep(transaction);
        }

        toast.add({ severity: 'success', summary: 'Success', detail: 'Transaction updated successfully', life: 3000 });
      } catch (error) {
        console.error('Error saving transaction:', error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save transaction', life: 3000 });
      } finally {
        transaction.saving = false;
      }
    };

    // Save all changes to file
    const saveAllChanges = async () => {
      savingAll.value = true;

      try {
        // First, save all modified transactions
        const changedTxs = transactions.value.filter(tx => isTransactionChanged(tx));

        // Save each changed transaction
        if (changedTxs.length > 0) {
          for (const tx of changedTxs) {
            const uuid = tx.meta.beanbot_uuid;
            await axios.put(`${API_BASE_URL}/transactions/${uuid}`, tx);
          }

          // Update original state after saving
          originalTransactions.value = _.cloneDeep(transactions.value);
          toast.add({ severity: 'success', summary: 'Success', detail: `Updated ${changedTxs.length} transactions`, life: 3000 });
        } else {
          toast.add({ severity: 'info', summary: 'Info', detail: 'No transaction changes detected', life: 3000 });
        }

        // Always save to file, even if no changes detected in the UI
        await axios.post(`${API_BASE_URL}/save`);
        toast.add({ severity: 'success', summary: 'Success', detail: 'All changes saved to disk', life: 3000 });

        // Reload transactions from file to reflect any backend changes
        await axios.post(`${API_BASE_URL}/reload`);

        // Reload the transactions from server to reflect any backend changes
        await loadTransactions();
        toast.add({ severity: 'success', summary: 'Success', detail: 'Transactions reloaded from file', life: 3000 });

      } catch (error) {
        console.error('Error saving changes:', error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save changes to file', life: 3000 });
      } finally {
        savingAll.value = false;
      }
    };

    // Reload data from disk
    const reloadFromDisk = async () => {
      reloading.value = true;

      try {
        // Reload transactions from file
        await axios.post(`${API_BASE_URL}/reload`);
        toast.add({ severity: 'success', summary: 'Success', detail: 'Transactions reloaded from disk', life: 3000 });

        // Reload the transactions in the UI
        await loadTransactions();
      } catch (error) {
        console.error('Error reloading from disk:', error);
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to reload from disk', life: 3000 });
      } finally {
        reloading.value = false;
      }
    };

    // Table row state
    const rowClassNameHandler = (data) => {
      return {
        'changed-row': isTransactionChanged(data),
        'p-highlight': selectedRows.value.some(row => row.meta.beanbot_uuid === data.meta.beanbot_uuid)
      };
    };

    // Helper methods for transaction data columns
    const getBookedAccount = (transaction) => {
      if (!transaction || !transaction.postings || transaction.postings.length === 0) {
        return 'N/A';
      }
      return transaction.postings[0].account;
    };

    const getBookedAmount = (transaction) => {
      if (!transaction || !transaction.postings || transaction.postings.length === 0) {
        return 'N/A';
      }

      const firstPosting = transaction.postings[0];
      if (firstPosting.units === "__MISSING__") {
        return 'None';
      }

      return `${firstPosting.units.number} ${firstPosting.units.currency}`;
    };

    const getCounterAccounts = (transaction) => {
      if (!transaction || !transaction.postings || transaction.postings.length <= 1) {
        return 'N/A';
      }

      const counterAccounts = transaction.postings.slice(1).map(p => p.account);

      if (counterAccounts.length === 1) {
        return counterAccounts[0];
      }

      return 'MULTIPLE';
    };

    // Custom sort handler
    const onSort = (event) => {
      const { field, order } = event;
      console.log('Sorting by field:', field, 'order:', order);

      // Clone the array to avoid reactivity issues
      const sortedData = [...transactions.value];

      sortedData.sort((a, b) => {
        let valueA, valueB;

        // Handle different field types
        if (field === 'date') {
          valueA = new Date(a[field] || '');
          valueB = new Date(b[field] || '');
          return (valueA - valueB) * order;
        }
        else if (field === '_bookedAmount') {
          // Extract numeric values from the booked amount
          valueA = a.postings && a.postings.length > 0 && a.postings[0].units && a.postings[0].units.number
            ? parseFloat(a.postings[0].units.number) || 0
            : 0;

          valueB = b.postings && b.postings.length > 0 && b.postings[0].units && b.postings[0].units.number
            ? parseFloat(b.postings[0].units.number) || 0
            : 0;

          return (valueA - valueB) * order;
        }
        else if (field === '_bookedAccount') {
          valueA = a.postings && a.postings.length > 0 ? a.postings[0].account || '' : '';
          valueB = b.postings && b.postings.length > 0 ? b.postings[0].account || '' : '';
          return valueA.localeCompare(valueB) * order;
        }
        else if (field === '_counterAccount') {
          valueA = a.postings && a.postings.length > 1 ? a.postings[1].account || '' : '';
          valueB = b.postings && b.postings.length > 1 ? b.postings[1].account || '' : '';
          return valueA.localeCompare(valueB) * order;
        }
        else if (field === 'tags') {
          valueA = (a.tags || []).join(',');
          valueB = (b.tags || []).join(',');
          return valueA.localeCompare(valueB) * order;
        }
        else {
          // Default string comparison for other fields
          valueA = a[field] || '';
          valueB = b[field] || '';

          if (typeof valueA === 'string' && typeof valueB === 'string') {
            return valueA.localeCompare(valueB) * order;
          } else {
            return ((valueA > valueB) ? 1 : -1) * order;
          }
        }
      });

      // Update the transactions with the sorted data
      transactions.value = sortedData;
    };

    // New methods for updating booked account and counter account
    const updateBookedAccount = (transaction) => {
      if (!transaction || !transaction.postings || transaction.postings.length === 0) {
        return;
      }

      // Update the account in the first posting
      transaction.postings[0].account = transaction._bookedAccount;
    };

    const updateCounterAccount = (transaction) => {
      if (!transaction || !transaction.postings || transaction.postings.length <= 1) {
        return;
      }

      const newCounterAccount = transaction._counterAccount;

      // If the transaction previously had multiple counter accounts
      if (transaction.postings.length > 2) {
        // Replace all counter accounts with a single account
        const secondPosting = transaction.postings[1];

        // Keep only the first two postings (booked account and first counter account)
        transaction.postings = transaction.postings.slice(0, 2);

        // Update the account of the second posting
        secondPosting.account = newCounterAccount;

        // Set missing values for the amount
        if (!secondPosting.units) {
          secondPosting.units = "__MISSING__";
        }
        secondPosting.units.number = null;
        secondPosting.units.currency = null;
      }
      // If the transaction has exactly one counter account, just update it
      else if (transaction.postings.length === 2) {
        transaction.postings[1].account = newCounterAccount;

        // If the counter account name was changed, set missing values
        if (transaction._counterAccount !== transaction.postings[1].account) {
          if (!transaction.postings[1].units) {
            transaction.postings[1].units = "__MISSING__";
          }
        }
      }
    };

    // Train the classifier model
    const trainModel = async () => {
      training.value = true;

      try {
        await axios.post(`${API_BASE_URL}/train`);
        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: 'Model trained successfully',
          life: 3000
        });
      } catch (error) {
        console.error('Error training model:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: `Failed to train model: ${error.response?.data?.detail || error.message}`,
          life: 3000
        });
      } finally {
        training.value = false;
      }
    };

    // Predict counter accounts for selected transactions
    const predictCounterAccounts = async () => {
      const selected = selectedRows.value;
      if (!selected.length) {
        toast.add({
          severity: 'warn',
          summary: 'Warning',
          detail: 'No transactions selected for prediction',
          life: 3000
        });
        return;
      }

      predicting.value = true;

      try {
        // Get transaction IDs
        const transactionIds = selected.map(tx => tx.meta.beanbot_uuid);

        // Call the prediction API
        const response = await axios.post(`${API_BASE_URL}/predict`, transactionIds);

        // Apply predictions
        const predictions = response.data.predictions;
        console.log('Predictions received:', predictions);

        let updatedCount = 0;

        // Loop through the selected transactions and apply predictions by index
        selected.forEach((transaction, index) => {
          const txId = transaction.meta.beanbot_uuid;
          const predictedAccount = predictions[index]; // Use index instead of txId as key

          console.log(`Transaction ${txId} (index ${index}):`, predictedAccount ? `Predicted: ${predictedAccount}` : 'No prediction');

          if (predictedAccount) {
            // Store original state before applying prediction (for revert functionality)
            if (!predictedTransactions.value.has(txId)) {
              predictedTransactions.value.set(txId, _.cloneDeep(transaction));
            }

            // Apply prediction
            if (transaction.postings.length > 1) {
              // If there are multiple counter accounts
              if (transaction.postings.length > 2) {
                // Keep only the first posting (booked account) and the second posting
                transaction.postings = transaction.postings.slice(0, 2);
              }

              // Update the counter account (second posting)
              transaction.postings[1].account = predictedAccount;
              transaction._counterAccount = predictedAccount;

              // Mark as predicted
              transaction.predicted = true;
              updatedCount++;

              console.log(`Updated transaction ${txId} with account: ${predictedAccount}`);
            }
          }
        });

        console.log(`Updated ${updatedCount} transactions out of ${selected.length} selected`);

        // Force UI refresh
        transactions.value = [...transactions.value];

        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: `Applied predictions for ${updatedCount} transactions`,
          life: 3000
        });
      } catch (error) {
        console.error('Error predicting counter accounts:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: `Failed to predict counter accounts: ${error.response?.data?.detail || error.message}`,
          life: 3000
        });
      } finally {
        predicting.value = false;
      }
    };

    // Revert a single prediction
    const revertPrediction = (transaction) => {
      const txId = transaction.meta.beanbot_uuid;

      if (predictedTransactions.value.has(txId)) {
        // Get the original state
        const originalTx = predictedTransactions.value.get(txId);

        // Restore postings
        transaction.postings = originalTx.postings;

        // Restore UI properties
        transaction._bookedAccount = transaction.postings.length > 0
          ? transaction.postings[0].account
          : '';

        // Restore counter account field
        if (transaction.postings.length > 1) {
          const counterAccounts = transaction.postings.slice(1).map(p => p.account);
          transaction._counterAccount = counterAccounts.length === 1
            ? counterAccounts[0]
            : 'MULTIPLE';
        } else {
          transaction._counterAccount = '';
        }

        // Remove predicted flag
        delete transaction.predicted;

        // Remove from the map
        predictedTransactions.value.delete(txId);

        toast.add({
          severity: 'info',
          summary: 'Reverted',
          detail: 'Prediction reverted',
          life: 2000
        });
      }
    };

    // Revert all predictions
    const revertAllPredictions = () => {
      if (predictedTransactions.value.size === 0) {
        return;
      }

      // Iterate through all transactions
      transactions.value.forEach(tx => {
        const txId = tx.meta.beanbot_uuid;

        if (predictedTransactions.value.has(txId)) {
          // Get the original state
          const originalTx = predictedTransactions.value.get(txId);

          // Restore postings
          tx.postings = originalTx.postings;

          // Restore UI properties
          tx._bookedAccount = tx.postings.length > 0
            ? tx.postings[0].account
            : '';

          // Restore counter account field
          if (tx.postings.length > 1) {
            const counterAccounts = tx.postings.slice(1).map(p => p.account);
            tx._counterAccount = counterAccounts.length === 1
              ? counterAccounts[0]
              : 'MULTIPLE';
          } else {
            tx._counterAccount = '';
          }

          // Remove predicted flag
          delete tx.predicted;
        }
      });

      // Clear the map
      predictedTransactions.value.clear();

      toast.add({
        severity: 'info',
        summary: 'Reverted',
        detail: 'All predictions reverted',
        life: 2000
      });
    };

    // Initialize
    onMounted(async () => {
      await loadReferenceData();
      await loadTransactions();
    });

    return {
      // State
      transactions,
      availableAccounts,
      availableTags,
      availableCurrencies,
      loading,
      savingAll,
      reloading,
      training,
      predicting,
      filters,
      tagDialogVisible,
      postingsDialogVisible,
      batchEditDialogVisible,
      newTagValue,
      currentTransaction,
      currentTaggedTransaction,
      totalItems,
      pageSize,
      first,
      batchEdit,
      transactionTable,
      selectedRows,
      filteredAccounts,
      predictedTransactions,

      // Computed
      selectedTransactions,
      allTagsInSelected,
      hasPredictions,

      // Methods
      loadTransactions,
      resetFilters,
      clearFilter,
      onPageChange,
      showTagInput,
      confirmAddTag,
      removeTag,
      editPostings,
      addPosting,
      removePosting,
      savePostings,
      searchAccounts,
      saveTransaction,
      saveAllChanges,
      reloadFromDisk,
      handleRowClick,
      onRowSelect,
      onRowUnselect,
      clearSelection,
      showBatchEditDialog,
      applyBatchEdit,
      isTransactionChanged,
      rowClassNameHandler,
      getBookedAccount,
      getBookedAmount,
      getCounterAccounts,
      updateBookedAccount,
      updateCounterAccount,
      onSort,
      trainModel,
      predictCounterAccounts,
      revertPrediction,
      revertAllPredictions
    };
  }
};
</script>

<style scoped>
.beancount-editor {
  width: 100%;
  margin: 0;
  padding: 1.25rem;
  box-sizing: border-box;
}

.filter-section {
  margin-bottom: 1.25rem;
  padding: 1rem;
  border: 1px solid var(--surface-border);
  border-radius: 4px;
  background-color: var(--surface-ground);
  width: 100%;
  box-sizing: border-box;
}

.loading-container {
  padding: 1.25rem;
}

.batch-actions {
  margin-bottom: 1rem;
}

.batch-buttons {
  margin-top: 0.5rem;
  display: flex;
  gap: 0.625rem;
}

.disabled-input {
  background-color: var(--surface-200);
  cursor: pointer;
}

.posting-editor {
  margin-bottom: 1rem;
  padding: 0.625rem;
  border: 1px solid var(--surface-border);
  border-radius: 4px;
}

/* PrimeVue-specific styling for changed rows */
:deep(.changed-row) {
  background-color: var(--p-orange-50) !important;
}

:deep(.p-datatable-tbody > tr.changed-row > td) {
  background-color: var(--p-orange-50) !important;
}

:deep(.p-datatable-tbody > tr.p-highlight.changed-row > td) {
  background-color: var(--p-orange-200) !important;
}

/* Make autocomplete take full width of its container */
:deep(.p-autocomplete) {
  width: 100%;
}

:deep(.p-autocomplete-input) {
  width: 100%;
}

/* Fix dropdown fullwidth */
:deep(.p-dropdown) {
  width: 100%;
}

/* Fix calendar fullwidth */
:deep(.p-calendar) {
  width: 100%;
}

/* Ensure tag container has spacing */
.tag-container {
  min-height: 2rem;
}

/* Make sure the multiselect is full-width */
:deep(.p-multiselect) {
  width: 100%;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
    gap: 0.625rem;
  }

  .action-buttons .p-button {
    width: 100%;
  }
}

/* Custom tag styling */
.custom-tag {
  background-color: var(--blue-100);
  color: var(--blue-900);
  font-size: 0.875rem;
  border-radius: 4px;
}

.custom-tag .p-button {
  margin-left: 4px;
  padding: 0;
  color: var(--blue-900);
}

.custom-tag .p-button:hover {
  background-color: var(--blue-200);
  color: var(--blue-900);
}

/* Predicted field styling */
.predicted-input {
  background-color: var(--cyan-50) !important;
  border-color: var(--cyan-200) !important;
}

:deep(.predicted-input input) {
  background-color: var(--cyan-50) !important;
}
</style>
