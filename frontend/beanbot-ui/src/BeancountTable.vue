<template>
  <div class="beancount-container">
    <h1>Beancount Entry Management</h1>

    <!-- Filters -->
    <el-card class="filter-card">
      <template #header>
        <div class="filter-header">
          <span>Filters</span>
          <el-button @click="resetFilters" size="small" type="primary">Reset Filters</el-button>
        </div>
      </template>
      <div class="filter-form">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="Date Range">
              <el-date-picker
                v-model="filters.dateRange"
                type="daterange"
                range-separator="To"
                start-placeholder="Start date"
                end-placeholder="End date"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Narration">
              <el-input
                v-model="filters.narration"
                placeholder="Search narration"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Tags">
              <el-select
                v-model="filters.tags"
                multiple
                filterable
                placeholder="Select tags"
                clearable
              >
                <el-option
                  v-for="tag in availableTags"
                  :key="tag"
                  :label="tag"
                  :value="tag"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Account">
              <el-select
                v-model="filters.account"
                filterable
                placeholder="Filter by account"
                clearable
              >
                <el-option
                  v-for="account in availableAccounts"
                  :key="account"
                  :label="account"
                  :value="account"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Counter Account">
              <el-select
                v-model="filters.counterAccount"
                filterable
                placeholder="Filter by counter account"
                clearable
              >
                <el-option
                  v-for="account in availableCounterAccounts"
                  :key="account"
                  :label="account"
                  :value="account"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- Data Table -->
    <el-card class="table-card">
      <template #header>
        <div class="table-header">
          <span>Beancount Entries</span>
          <div>
            <el-button @click="toggleSelection" size="small">Toggle Selection</el-button>
            <el-button type="primary" size="small" :disabled="selectedEntries.length === 0">
              Batch Edit ({{ selectedEntries.length }})
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        ref="multipleTable"
        :data="filteredData"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="confirmed" label="Confirmed" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.confirmed"
              inline-prompt
              :active-text="'Y'"
              :inactive-text="'N'"
            />
          </template>
        </el-table-column>
        <el-table-column prop="date" label="Date" sortable width="120" />
        <el-table-column prop="narration" label="Narration" show-overflow-tooltip>
          <template #default="scope">
            <div class="narration-cell">
              {{ scope.row.narration }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="account" label="Account" show-overflow-tooltip width="220" />
        <el-table-column prop="counterAccount" label="Counter Account" show-overflow-tooltip width="220" />
        <el-table-column prop="tags" label="Tags" width="150">
          <template #default="scope">
            <div class="tag-container">
              <el-tag
                v-for="tag in scope.row.tags"
                :key="tag"
                size="small"
                effect="plain"
                class="mx-1"
              >
                {{ tag }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="120">
          <template #default="scope">
            <el-button size="small" @click="editEntry(scope.row)">Edit</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[5, 10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          :total="filteredData.length"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';

// Sample data transformed from the beancount entries
const beancountEntries = ref([
  {
    id: 1,
    confirmed: true,
    date: '2024-09-01',
    narration: '支付宝－中移动金融科技有限公司',
    account: 'Liabilities:Credit:Citic:UnionPay',
    amount: '-49.89',
    currency: 'CNY',
    counterAccount: 'Expenses:Food:Restaurant',
    booked_on: '2024-09-01',
    tags: ['_new_dt']
  },
  {
    id: 2,
    confirmed: true,
    date: '2024-09-09',
    narration: '支付宝－杭州今日卖场供应链管理有限公司',
    account: 'Liabilities:Credit:Citic:UnionPay',
    amount: '-12.42',
    currency: 'CNY',
    counterAccount: 'Expenses:Food:Restaurant',
    booked_on: '2024-09-09',
    tags: ['_new_dt']
  },
  {
    id: 3,
    confirmed: true,
    date: '2024-09-10',
    narration: '支付宝－优趣汇（上海）供应链管理有限公司',
    account: 'Liabilities:Credit:Citic:UnionPay',
    amount: '-124.90',
    currency: 'CNY',
    counterAccount: 'Expenses:Food:Restaurant',
    booked_on: '2024-09-10',
    tags: ['_new_dt']
  },
  {
    id: 4,
    confirmed: true,
    date: '2024-09-15',
    narration: '支付宝－App Store * Apple Music',
    account: 'Liabilities:Credit:Citic:UnionPay',
    amount: '-15.00',
    currency: 'CNY',
    counterAccount: 'Expenses:Food:Restaurant',
    booked_on: '2024-09-15',
    tags: ['*new_dt']
  },
  {
    id: 5,
    confirmed: true,
    date: '2024-09-25',
    narration: '京东支付－京东商城业务',
    account: 'Liabilities:Credit:Citic:UnionPay',
    amount: '-228.73',
    currency: 'CNY',
    counterAccount: 'Expenses:Food:Restaurant',
    booked_on: '2024-09-25',
    tags: ['_new_dt']
  }
]);

// Filter state
const filters = ref({
  dateRange: [],
  narration: '',
  tags: [],
  account: '',
  counterAccount: ''
});

// Pagination
const currentPage = ref(1);
const pageSize = ref(10);

// Selected entries for batch editing
const selectedEntries = ref([]);
const multipleTable = ref(null);

// Extract available filter options from data
const availableTags = computed(() => {
  const tagSet = new Set();
  beancountEntries.value.forEach(entry => {
    entry.tags.forEach(tag => tagSet.add(tag));
  });
  return Array.from(tagSet);
});

const availableAccounts = computed(() => {
  const accounts = new Set();
  beancountEntries.value.forEach(entry => {
    accounts.add(entry.account);
  });
  return Array.from(accounts);
});

const availableCounterAccounts = computed(() => {
  const accounts = new Set();
  beancountEntries.value.forEach(entry => {
    accounts.add(entry.counterAccount);
  });
  return Array.from(accounts);
});

// Apply filters to data
const filteredData = computed(() => {
  return beancountEntries.value.filter(entry => {
    // Date range filter
    if (filters.value.dateRange && filters.value.dateRange.length === 2) {
      const [startDate, endDate] = filters.value.dateRange;
      if (entry.date < startDate || entry.date > endDate) {
        return false;
      }
    }

    // Narration filter
    if (filters.value.narration && !entry.narration.toLowerCase().includes(filters.value.narration.toLowerCase())) {
      return false;
    }

    // Tags filter
    if (filters.value.tags && filters.value.tags.length > 0) {
      if (!filters.value.tags.some(tag => entry.tags.includes(tag))) {
        return false;
      }
    }

    // Account filter
    if (filters.value.account && entry.account !== filters.value.account) {
      return false;
    }

    // Counter account filter
    if (filters.value.counterAccount && entry.counterAccount !== filters.value.counterAccount) {
      return false;
    }

    return true;
  });
});

// Event handlers
function resetFilters() {
  filters.value = {
    dateRange: [],
    narration: '',
    tags: [],
    account: '',
    counterAccount: ''
  };
}

function handleSelectionChange(val) {
  selectedEntries.value = val;
}

function toggleSelection() {
  if (selectedEntries.value.length > 0) {
    multipleTable.value.clearSelection();
  } else {
    beancountEntries.value.forEach(row => {
      multipleTable.value.toggleRowSelection(row, true);
    });
  }
}

function editEntry(row) {
  ElMessage({
    message: `Editing entry: ${row.date} ${row.narration}`,
    type: 'info',
  });
  // This would typically open a dialog for editing
}

function handleSizeChange(val) {
  pageSize.value = val;
}

function handleCurrentChange(val) {
  currentPage.value = val;
}

// Initialize
onMounted(() => {
  console.log('Beancount UI mounted!');
});
</script>

<style>
.beancount-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.filter-card, .table-card {
  margin-bottom: 20px;
}

.filter-header, .table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-form {
  margin-top: 15px;
}

.tag-container {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.narration-cell {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
