export type Role = 'admin' | 'hr' | 'manager' | 'employee';

export interface UserSummary {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  org_id: string;
}

export interface Employee {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  department: string;
  designation: string;
  status: string;
  org_id: string;
}

export interface LeaveApplication {
  id: string;
  user_id: string;
  org_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
}

export interface ExpenseClaim {
  id: string;
  user_id: string;
  org_id: string;
  category: string;
  amount: number;
  currency: string;
  description: string;
  expense_date: string;
  status: string;
}
