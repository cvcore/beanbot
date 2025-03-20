<template>
  <div class="beancount-editor">
    <h1>Beancount Entries Editor</h1>

    <!-- Filter section -->
    <div class="filter-section">
      <el-row :gutter="10">
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-input
            v-model="filters.narration"
            placeholder="Filter by Narration"
            clearable
            @clear="loadTransactions"
            @keyup.enter="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-input
            v-model="filters.account"
            placeholder="Filter by Account"
            clearable
            @clear="loadTransactions"
            @keyup.enter="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-select
            v-model="filters.tag"
            placeholder="Filter by Tag"
            clearable
            style="width: 100%"
            @clear="loadTransactions"
            @change="loadTransactions"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-col>
      </el-row>
      <el-row :gutter="10" style="margin-top: 10px;">
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-date-picker
            v-model="filters.fromDate"
            type="date"
            placeholder="From Date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
            @clear="loadTransactions"
            @change="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-date-picker
            v-model="filters.toDate"
            type="date"
            placeholder="To Date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
            @clear="loadTransactions"
            @change="loadTransactions"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :md="8" :lg="8">
          <el-select
            v-model="filters.currency"
            placeholder="Filter by Currency"
            clearable
            style="width: 100%;"
            @clear="loadTransactions"
            @change="loadTransactions"
          >
            <el-option
              v-for="currency in availableCurrencies"
              :key="currency"
              :label="currency"
              :value="currency"
            />
          </el-select>
        </el-col>
      </el-row>
      <el-row :gutter="10" style="margin-top: 10px;">
        <el-col :span="24">
          <el-button type="primary" @click="loadTransactions">
            <el-icon><Search /></el-icon> Search
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon> Reset Filters
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- Loading indicator -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- Batch edit actions (visible when transactions are selected) -->
    <div v-if="!loading && selectedTransactions.length > 0" class="batch-actions">
      <el-alert
        title="Batch Edit Mode"
        type="info"
        :closable="false"
        show-icon
      >
        <template #default>
          <span>{{ selectedTransactions.length }} transactions selected.</span>
          <div class="batch-buttons">
            <el-button size="small" @click="clearSelection">Clear Selection</el-button>
            <el-button type="primary" size="small" @click="showBatchEditDialog">Batch Edit</el-button>
          </div>
        </template>
      </el-alert>
    </div>

    <!-- Table section -->
    <div v-if="!loading">
      <el-table
        :data="transactions"
        :row-class-name="rowClassNameHandler"
        style="width: 100%"
        border
        v-loading="loading"
        @row-click="handleRowClick"
        ref="transactionTable"
      >
        <!-- Selection column -->
        <el-table-column type="selection" width="55" />

        <el-table-column label="Flag" width="80" align="center">
          <template #default="scope">
            <el-select v-model="scope.row.flag" style="width: 60px">
              <el-option label="*" value="*" />
              <el-option label="!" value="!" />
            </el-select>
          </template>
        </el-table-column>

        <el-table-column label="Date" width="150" align="center">
          <template #default="scope">
            <el-date-picker
              v-model="scope.row.date"
              type="date"
              placeholder="Select date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </template>
        </el-table-column>

        <el-table-column label="Payee" min-width="150">
          <template #default="scope">
            <el-input v-model="scope.row.payee" placeholder="Enter payee" />
          </template>
        </el-table-column>

        <el-table-column label="Narration" min-width="200">
          <template #default="scope">
            <el-input v-model="scope.row.narration" placeholder="Enter narration" />
          </template>
        </el-table-column>

        <el-table-column label="Booked Account" min-width="180">
          <template #default="scope">
            <el-autocomplete
              v-model="scope.row._bookedAccount"
              :fetch-suggestions="queryAccounts"
              placeholder="Enter account"
              style="width: 100%"
              @change="updateBookedAccount(scope.row)"
              @select="updateBookedAccount(scope.row)"
            />
          </template>
        </el-table-column>

        <el-table-column label="Booked Amount" min-width="150">
          <template #default="scope">
            <span>{{ getBookedAmount(scope.row) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Counter Account(s)" min-width="180">
          <template #default="scope">
            <el-autocomplete
              v-model="scope.row._counterAccount"
              :fetch-suggestions="queryAccounts"
              placeholder="Enter account"
              style="width: 100%"
              @change="updateCounterAccount(scope.row)"
              @select="updateCounterAccount(scope.row)"
              :class="{ 'disabled-input': getCounterAccounts(scope.row) === 'MULTIPLE' }"
              :title="getCounterAccounts(scope.row) === 'MULTIPLE' ?
                'Multiple counter accounts. Editing will replace them all with a single account.' : ''"
            />
            <span v-if="getCounterAccounts(scope.row) === 'MULTIPLE'" class="multiple-indicator">
              (MULTIPLE)
            </span>
          </template>
        </el-table-column>

        <el-table-column label="Sum Counter Amounts" min-width="180">
          <template #default="scope">
            <span>{{ getSumCounterAmounts(scope.row) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Tags" min-width="150">
          <template #default="scope">
            <div class="tag-container">
              <el-tag
                v-for="tag in scope.row.tags"
                :key="tag"
                closable
                class="tag-item"
                @close="removeTag(scope.row, tag)"
              >
                {{ tag }}
              </el-tag>
              <el-button
                size="small"
                type="primary"
                plain
                @click="showTagInput(scope.row)"
              >
                + Tag
              </el-button>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="180" align="center">
          <template #default="scope">
            <el-button
              size="small"
              type="primary"
              @click.stop="editPostings(scope.row)"
            >
              Edit Postings
            </el-button>
            <el-button
              size="small"
              type="success"
              circle
              @click.stop="saveTransaction(scope.row)"
              :loading="scope.row.saving"
            >
              <el-icon><Check /></el-icon>
            </el-button>
          </template>
        </el-table-column>

        <!-- Custom class for highlighting changed rows -->
        <template #row-class="{ row }">
          {{ isTransactionChanged(row) ? 'changed-row' : '' }}
        </template>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalItems"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <!-- Save all changes button -->
      <div class="action-buttons">
        <el-button type="success" @click="saveAllChanges" :loading="savingAll">
          <el-icon><Upload /></el-icon> Save All Changes
        </el-button>
      </div>
    </div>

    <!-- Tag Input Dialog -->
    <el-dialog
      v-model="tagDialogVisible"
      title="Add Tag"
      width="30%"
    >
      <el-input
        v-model="newTagValue"
        placeholder="Enter tag name"
        @keyup.enter="confirmAddTag"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="tagDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="confirmAddTag">Confirm</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Postings Dialog -->
    <el-dialog
      v-model="postingsDialogVisible"
      title="Edit Postings"
      width="80%"
    >
      <div v-if="currentTransaction">
        <div v-for="(posting, index) in currentTransaction.postings" :key="index" class="posting-editor">
          <el-divider v-if="index > 0" />
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="Account">
                <el-autocomplete
                  v-model="posting.account"
                  :fetch-suggestions="queryAccounts"
                  placeholder="Enter account"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="Amount">
                <el-input v-model="posting.units.number" placeholder="Amount" />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="Currency">
                <el-select v-model="posting.units.currency" placeholder="Currency" style="width: 100%">
                  <el-option
                    v-for="currency in availableCurrencies"
                    :key="currency"
                    :label="currency"
                    :value="currency"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="Missing">
                <el-switch v-model="posting.units.is_missing" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row>
            <el-col :span="24" class="posting-actions">
              <el-button
                v-if="currentTransaction.postings.length > 2"
                type="danger"
                size="small"
                @click="removePosting(index)"
              >
                Remove Posting
              </el-button>
            </el-col>
          </el-row>
        </div>

        <div class="posting-actions">
          <el-button type="primary" @click="addPosting">
            Add Posting
          </el-button>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="postingsDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="savePostings">Save Postings</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Batch Edit Dialog -->
    <el-dialog
      v-model="batchEditDialogVisible"
      title="Batch Edit Transactions"
      width="60%"
    >
      <div>
        <p>Editing {{ selectedTransactions.length }} transactions</p>

        <el-form label-width="120px">
          <el-form-item label="Flag">
            <el-select v-model="batchEdit.flag" placeholder="Select flag" clearable>
              <el-option label="*" value="*" />
              <el-option label="!" value="!" />
            </el-select>
          </el-form-item>

          <el-form-item label="Add tags">
            <el-select v-model="batchEdit.addTags" placeholder="Select tags to add" multiple>
              <el-option
                v-for="tag in availableTags"
                :key="tag"
                :label="tag"
                :value="tag"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="Remove tags">
            <el-select v-model="batchEdit.removeTags" placeholder="Select tags to remove" multiple>
              <el-option
                v-for="tag in allTagsInSelected"
                :key="tag"
                :label="tag"
                :value="tag"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="batchEditDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="applyBatchEdit">Apply Changes</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, nextTick } from 'vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import { Delete, Plus, Upload, Check, Search, Refresh } from '@element-plus/icons-vue';
import axios from 'axios';
import _ from 'lodash';

// API base URL - change this to match your FastAPI server
const API_BASE_URL = 'http://localhost:8000/api';

export default {
  name: 'BeancountEditor',
  components: {
    Delete,
    Plus,
    Upload,
    Check,
    Search,
    Refresh
  },
  setup() {
    // State
    const transactions = ref([]);
    const originalTransactions = ref([]); // For tracking changes
    const availableAccounts = ref([]);
    const availableTags = ref([]);
    const availableCurrencies = ref([]);
    const loading = ref(false);
    const savingAll = ref(false);
    const tagDialogVisible = ref(false);
    const postingsDialogVisible = ref(false);
    const batchEditDialogVisible = ref(false);
    const newTagValue = ref('');
    const currentTransaction = ref(null);
    const currentTaggedTransaction = ref(null);
    const totalItems = ref(0);
    const currentPage = ref(1);
    const pageSize = ref(20);
    const lastSelectedIndex = ref(-1);
    const transactionTable = ref(null);

    // Batch edit state
    const batchEdit = reactive({
      flag: '',
      addTags: [],
      removeTags: []
    });

    // Filters
    const filters = reactive({
      narration: '',
      account: '',
      fromDate: '',
      toDate: '',
      tag: '',
      currency: ''
    });

    // Computed properties
    const selectedTransactions = computed(() => {
      if (!transactionTable.value) return [];
      return transactionTable.value.getSelectionRows();
    });

    const allTagsInSelected = computed(() => {
      const allTags = new Set();
      selectedTransactions.value.forEach(tx => {
        tx.tags.forEach(tag => allTags.add(tag));
      });
      return Array.from(allTags);
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
        ElMessage.error('Failed to load reference data');
      }
    };

    // Load transactions with current filters and pagination
    const loadTransactions = async () => {
      loading.value = true;

      try {
        // Build query parameters
        const params = {
          page: currentPage.value,
          page_size: pageSize.value
        };

        if (filters.narration) params.narration = filters.narration;
        if (filters.account) params.account = filters.account;
        if (filters.fromDate) params.from_date = filters.fromDate;
        if (filters.toDate) params.to_date = filters.toDate;
        if (filters.tag) params.tag = filters.tag;
        if (filters.currency) params.currency = filters.currency;

        const response = await axios.get(`${API_BASE_URL}/transactions`, { params });

        // Update state
        transactions.value = response.data.data.items;

        // Add saving flag to each transaction
        transactions.value.forEach(tx => {
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
        nextTick(() => {
          if (transactionTable.value) {
            transactionTable.value.clearSelection();
          }
        });

      } catch (error) {
        console.error('Error loading transactions:', error);
        ElMessage.error('Failed to load transactions');
      } finally {
        loading.value = false;
      }
    };

    // Reset all filters
    const resetFilters = () => {
      Object.keys(filters).forEach(key => {
        filters[key] = '';
      });
      loadTransactions();
    };

    // Pagination event handlers
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize;
      loadTransactions();
    };

    const handleCurrentChange = (newPage) => {
      currentPage.value = newPage;
      loadTransactions();
    };

    // Selection handling
    const handleRowClick = (row, column, event) => {
      if (!transactionTable.value) return;

      const index = transactions.value.findIndex(t => t.meta.beanbot_uuid === row.meta.beanbot_uuid);
      if (index === -1) return;

      // Shift key for range selection
      if (event.shiftKey && lastSelectedIndex.value >= 0) {
        const start = Math.min(lastSelectedIndex.value, index);
        const end = Math.max(lastSelectedIndex.value, index);

        for (let i = start; i <= end; i++) {
          transactionTable.value.toggleRowSelection(transactions.value[i], true);
        }
      }
      // Cmd/Ctrl key for individual toggle
      else if (event.metaKey || event.ctrlKey) {
        transactionTable.value.toggleRowSelection(row);
      }
      // Normal click
      else {
        transactionTable.value.clearSelection();
        transactionTable.value.toggleRowSelection(row, true);
      }

      lastSelectedIndex.value = index;
    };

    // Clear all selections
    const clearSelection = () => {
      if (transactionTable.value) {
        transactionTable.value.clearSelection();
      }
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
          currency: availableCurrencies.value[0] || 'USD',
          is_missing: false
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

    // Account autocomplete
    const queryAccounts = (queryString, callback) => {
      const results = queryString
        ? availableAccounts.value.filter(account =>
            account.toLowerCase().includes(queryString.toLowerCase())
          )
        : availableAccounts.value;

      callback(results.map(account => ({ value: account })));
    };

    // Batch editing
    const showBatchEditDialog = () => {
      // Reset batch edit form
      batchEdit.flag = '';
      batchEdit.addTags = [];
      batchEdit.removeTags = [];

      batchEditDialogVisible.value = true;
    };

    const applyBatchEdit = () => {
      const selected = selectedTransactions.value;
      if (!selected.length) return;

      selected.forEach(transaction => {
        // Update flag if specified
        if (batchEdit.flag) {
          transaction.flag = batchEdit.flag;
        }

        // Add tags
        if (batchEdit.addTags.length) {
          const currentTags = new Set(transaction.tags);
          batchEdit.addTags.forEach(tag => currentTags.add(tag));
          transaction.tags = Array.from(currentTags);
        }

        // Remove tags
        if (batchEdit.removeTags.length) {
          transaction.tags = transaction.tags.filter(tag =>
            !batchEdit.removeTags.includes(tag)
          );
        }
      });

      batchEditDialogVisible.value = false;
      ElMessage.success(`Changes applied to ${selected.length} transactions`);
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

        ElMessage.success('Transaction updated successfully');
      } catch (error) {
        console.error('Error saving transaction:', error);
        ElMessage.error('Failed to save transaction');
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
          ElMessage.success(`Updated ${changedTxs.length} transactions`);
        } else {
          ElMessage.info('No transaction changes detected');
        }

        // Always save to file, even if no changes detected in the UI
        await axios.post(`${API_BASE_URL}/save`);
        ElMessage.success('All changes saved to disk');

      } catch (error) {
        console.error('Error saving changes:', error);
        ElMessage.error('Failed to save changes to file');
      } finally {
        savingAll.value = false;
      }
    };

    // Initialize
    onMounted(async () => {
      await loadReferenceData();
      await loadTransactions();
    });

    // Table row state
    const rowClassNameHandler = ({ row }) => {
      return isTransactionChanged(row) ? 'changed-row' : '';
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
      if (firstPosting.units.is_missing) {
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

    const getSumCounterAmounts = (transaction) => {
      if (!transaction || !transaction.postings || transaction.postings.length <= 1) {
        return 'N/A';
      }

      // Check if any counter account has is_missing: true
      const hasMissingAmount = transaction.postings.slice(1).some(p =>
        p.units && p.units.is_missing
      );

      if (hasMissingAmount) {
        return 'None';
      }

      // Group counter amounts by currency
      const amountsByCurrency = {};
      transaction.postings.slice(1).forEach(posting => {
        if (posting.units && posting.units.number && posting.units.currency) {
          const currency = posting.units.currency;
          const amount = parseFloat(posting.units.number);

          if (!amountsByCurrency[currency]) {
            amountsByCurrency[currency] = 0;
          }

          amountsByCurrency[currency] += amount;
        }
      });

      // Format the sums by currency
      const formattedSums = Object.entries(amountsByCurrency).map(([currency, amount]) =>
        `${amount.toFixed(2)} ${currency}`
      );

      return formattedSums.join(', ') || 'None';
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

        // Set is_missing = true for the amount
        if (!secondPosting.units) {
          secondPosting.units = {};
        }
        secondPosting.units.is_missing = true;
        secondPosting.units.number = null;
        secondPosting.units.currency = null;
      }
      // If the transaction has exactly one counter account, just update it
      else if (transaction.postings.length === 2) {
        transaction.postings[1].account = newCounterAccount;

        // If the counter account name was changed, set is_missing = true
        if (transaction._counterAccount !== transaction.postings[1].account) {
          if (!transaction.postings[1].units) {
            transaction.postings[1].units = {};
          }
          transaction.postings[1].units.is_missing = true;
          transaction.postings[1].units.number = null;
          transaction.postings[1].units.currency = null;
        }
      }
    };

    return {
      // State
      transactions,
      availableAccounts,
      availableTags,
      availableCurrencies,
      loading,
      savingAll,
      filters,
      tagDialogVisible,
      postingsDialogVisible,
      batchEditDialogVisible,
      newTagValue,
      currentTransaction,
      currentTaggedTransaction,
      totalItems,
      currentPage,
      pageSize,
      batchEdit,
      transactionTable,

      // Computed
      selectedTransactions,
      allTagsInSelected,

      // Methods
      loadTransactions,
      resetFilters,
      handleSizeChange,
      handleCurrentChange,
      showTagInput,
      confirmAddTag,
      removeTag,
      editPostings,
      addPosting,
      removePosting,
      savePostings,
      queryAccounts,
      saveTransaction,
      saveAllChanges,
      handleRowClick,
      clearSelection,
      showBatchEditDialog,
      applyBatchEdit,
      isTransactionChanged,
      rowClassNameHandler,
      getBookedAccount,
      getBookedAmount,
      getCounterAccounts,
      getSumCounterAmounts,
      updateBookedAccount,
      updateCounterAccount
    };
  }
};
</script>

<style scoped>
.beancount-editor {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.tag-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.posting-editor {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.posting-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.loading-container {
  padding: 20px;
}

.batch-actions {
  margin-bottom: 15px;
}

.batch-buttons {
  margin-top: 8px;
  display: flex;
  gap: 10px;
}

.multiple-indicator {
  color: #909399;
  font-size: 12px;
  margin-left: 5px;
}

.disabled-input {
  background-color: #f5f7fa;
  cursor: pointer;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
    gap: 10px;
  }

  .action-buttons .el-button {
    width: 100%;
  }
}
</style>


<style>

.el-table .changed-row {
  --el-table-tr-bg-color: var(--el-color-warning-light-9);
}
.el-table .success-row {
  --el-table-tr-bg-color: var(--el-color-success-light-9);
}
</style>
